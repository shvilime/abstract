# -*- coding: utf-8 -*-
import os
import re
import cgi
import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth
from requests import Session, Response, HTTPError, ConnectionError, Timeout
from typing import Union, List, Optional, Dict, Any, Type, Pattern, Text

from .strategies import NullExtractStrategy, JSONExtractStrategy, ZIPJSONExtractStrategy, XMLExtractStrategy
from .strategies import DeserializedHTTPResponse, DeserializedHTTPRequestBody
from .utils import curlify
from ..abstractpipeline import AbstractFactory, ExtractStrategy
from ..constants import TR


@dataclass()
class ServiceMethod:
    """
    Метод API HTTP сервиса
    """
    url: str
    headers: dict
    alias: str
    method: str
    decode: Optional[str] = None
    timeout: Optional[int] = None


class AdvanceSession(Session):
    config: Dict
    host: str
    port: int
    timeout: int

    def __init__(self, config: Dict) -> None:
        """
        Настройка подключения

        Args:
            config: Словарь с настройками подключения
        """
        super(AdvanceSession, self).__init__()
        self.config = config
        self.__setup_session()

    def __setup_session(self):
        """
        Настройка подключения через requests

        Returns:
            Session
        """
        self.host = self.config.get("host")
        self.port = self.config.get("port")
        self.timeout = self.config.get("timeout", TR.SESSION_TIMEOUT)
        self.verify = self.config.get("verify")

        if not self.host:
            raise ValueError("Не задан адрес хоста")

        if not self.port:
            raise ValueError("Не задан порт")

        auth_type: Optional[str] = self.config.get("auth_type")
        username: Optional[str] = self.config.get("username")
        password: Optional[str] = self.config.get("password")

        if auth_type == TR.AUTH_METHOD_BASIC:
            self.auth = HTTPBasicAuth(username, password)
        elif auth_type is None:
            self.auth = None
        else:
            raise NotImplementedError(f"{auth_type} метод идентификации не реализован")


class HTTPFactory(AbstractFactory):
    """
    Фабрика коннектов к шине ГК
    """
    __config: Dict
    __sessions: Dict[str, AdvanceSession]
    __routing: Dict[str, ServiceMethod]
    __dynamic_header_patten: Pattern[str]
    __extract_strategies: Dict[Any, Type[ExtractStrategy]]

    def __init__(self, config: Dict) -> None:
        """
        Настройка подключения

        Args:
            config: Словарь с настройками подключения
        """
        self.logger = logging.getLogger(__name__)
        self.__config = config
        self.__sessions = self.__setup_sessions()
        self.__routing = self.__setup_scheme()
        self.__dynamic_header_patten = re.compile(r"\$\(([a-zA-Z_$][a-zA-Z_$0-9]*)\)")
        self.__extract_strategies = {
            TR.MIME_APPLICATION_JSON: JSONExtractStrategy,
            TR.MIME_APPLICATION_XML: XMLExtractStrategy,
            TR.MIME_APPLICATION_OCTET_STREAM: NullExtractStrategy,
            TR.MIME_APPLICATION_ZIP: ZIPJSONExtractStrategy,
            TR.MIME_TEXT_HTML: NullExtractStrategy,
            TR.MIME_TEXT_PLAIN: NullExtractStrategy
        }

    def __setup_scheme(self) -> Dict[str, ServiceMethod]:
        """
        Парсинг схемы API сервиса

        Returns:
            Dict[str, ServiceMethod]
        """
        scheme: Union[dict, Text] = self.__config.get("scheme")

        if isinstance(scheme, str):
            if not os.path.exists(scheme):
                raise OSError(f"Схема {scheme} не найдена")

            with open(scheme) as descriptor:
                scheme: dict = json.load(descriptor)

        paths: List[Dict] = scheme.get("paths", [])

        if not paths:
            raise ValueError("Схема должна содержать описание методов. Атрибут paths не найден.")

        return {path["alias"]: ServiceMethod(**path) for path in paths}

    def __setup_sessions(self):
        """
        Настройка подключения через requests

        Returns:
            Sessions: Словарь с настроенными сессиями
        """

        # Получим список настрок сессии
        config: Dict = self.__config.get('sessions', {})
        if not config:
            raise ValueError("Не заданы настройки сессий. Проверьте в конфигурации раздел transport.sessions")

        sessions: Dict[str, AdvanceSession] = {}
        for item in config:
            sessions[item.get("alias").lower()] = AdvanceSession(item)

        return sessions

    def __get_dynamic_variable(self, variable: str, values: Dict) -> str:
        """
        Замещает название динамической переменной ее значением

        Args:
            variable: Строка, содержащая шаблоны с названиями динамических переменных

        Returns:
              Строка с подставленными значениями

        """
        for item in re.findall(self.__dynamic_header_patten, variable):
            value = values.get(item)
            if value is None:
                raise ValueError(f"Не задано значение для динамической переменной {item}")
            variable = re.sub(self.__dynamic_header_patten, value, variable, 1)

        return variable

    def execute(
            self,
            method: str,
            data: DeserializedHTTPRequestBody = None,
            json_data: Optional[Any] = None,
            zip_file: Optional[Dict] = None,
            dynamic_values: Optional[Dict] = None,
            extract_strategy: Optional[Type[ExtractStrategy]] = None,
            raise_on_http_error: bool = True,
            **kwargs
    ) -> DeserializedHTTPResponse:
        """
        Выполняет HTTP запрос к серверу ГК

        Args:
            method: Алиас метода API, описанного в конфигураторе клиента
            data: Тело запроса
            json_data: json тело запроса
            zip_file: zip-файл
            dynamic_values: значения для подстановки в заголовки
            extract_strategy: Пользовательская стратегия извлечения данных
            raise_on_http_error: Вызывать исключение при статусах ответа > 399
            kwargs: параметры url строки "?key2=value2&key1=value1"

        Returns:
            DeserializedHTTPResponse: Ответ сервера

        Example:

            .. code-block:: python

                response: Dict = self.transport['utm'].execute(
                    method="hash",
                    data=hash_info.to_primitive(),
                    dynamic_values={"whscode": "332004"},
                    extract_strategy: XMLExtractStrategy,
                    refresh="true"
                )
        """
        if not dynamic_values:
            dynamic_values = {}

        response: Optional[Response] = None

        # Получим КОПИЮ! настройки метода запроса из конфигурации
        service_method: Optional[ServiceMethod] = deepcopy(self.__routing.get(method))
        if not service_method:
            raise ValueError(f"Метод {method} не найден. Должен быть один из {', '.join(self.__routing.keys())}")

        # Запрос будет последовательно выполняться для всех сессий, заданных в конфигурации, до успеха
        for i, node in enumerate(self.__sessions.items()):
            key, session = node
            self.logger.debug(f"Попытка выполнения {method} в рамках сессии: {key}")

            # Настроим динамические заголовки запроса для текущей сессии
            for header, variable in service_method.headers.items():
                service_method.headers[header] = self.__get_dynamic_variable(variable, dynamic_values)

            # Настроим динамический URL запроса для текущей сессии
            service_method.url = self.__get_dynamic_variable(service_method.url, dynamic_values)

            # Установим для сессии дефолтные заголовки
            session.headers.update(self.__config.get("default_headers", {}))

            # Попробуем выполнить запрос в рамках сессии, если ошибка то следующей и т.д.
            try:
                self.logger.debug(f"Тип запроса: {service_method.method}\n"
                                  f"URL - {session.host}:{session.port}/{service_method.url}\n"
                                  f"Заголовки { {**session.headers, **service_method.headers} }\n"
                                  f"Данные: data={data} json={json_data} files={zip_file}")

                response: Response = getattr(session, service_method.method.lower())(
                    f'{session.host}:{session.port}/{service_method.url}',
                    timeout=service_method.timeout or session.timeout,
                    headers=service_method.headers,
                    data=data,
                    json=json_data,
                    files=deepcopy(zip_file),
                    params=kwargs
                )
                # Проверим код ответа на допустимый, если такая проверка не отключена
                response.raise_for_status() if raise_on_http_error else None
                break

            except (HTTPError, ConnectionError, Timeout) as e:
                self.logger.exception(f"Ошибка выполнения запроса к HTTP серверу: {str(e)}")
                self.logger.info("Для воспроизведения данной ошибки можно попробовать выполнить CURL запрос: \n")
                self.logger.info(curlify(
                    f'{session.host}:{session.port}/{service_method.url}', service_method.method, session,
                    data, json_data, zip_file, **kwargs
                ))
                if i == len(self.__sessions) - 1:
                    raise

        self.logger.debug(f"{response.status_code}: Ответ от {response.request.url}\n"
                          f"Заголовки: {response.headers}\n"
                          f"Контент: {response.content}")

        # Если не задана пользовательская стратегия извлечения данных - установим стратегию по типу контента
        mimetype, options = cgi.parse_header(response.headers.get("Content-Type", TR.MIME_APPLICATION_OCTET_STREAM))
        if not extract_strategy:
            extract_strategy = self.__extract_strategies.get(mimetype, NullExtractStrategy)

        return extract_strategy().extract(response, service_method.decode or options.get("charset", None))

    def acquire(self):
        raise NotImplementedError()
