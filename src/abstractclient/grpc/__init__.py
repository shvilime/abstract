# -*- coding: utf-8 -*-
import grpc
import logging
from importlib import import_module
from typing import Dict, Tuple, List, Optional, Any
from google.protobuf.reflection import GeneratedProtocolMessageType

from .. import environment
from ..abstractpipeline import AbstractFactory
from ..constants import TR
from ..utils import gzip_data

MAX_LOG_LENGTH: int = environment.get("MAX_LOG_LENGTH", 5000)


class GRPCFactory(AbstractFactory):
    """
    Фабрика коннектов gRPC
    """
    __timeout: int
    __channels: Dict[str, grpc.Channel] = dict()
    __stubs: Dict[Tuple[str, str], Any] = dict()
    __metadata: List[Tuple[str, str]] = list()

    def __init__(self, config: Dict):
        """
        Настройка подключения

        Args:
            config: Словарь с настройками подключения

        """
        self.logger = logging.getLogger(__name__)
        self.__config = config
        self.setup_channels()
        self.setup_stubs()

    def __del__(self):
        for name, chanel in self.__channels.items():
            chanel.close()

    def setup_channels(self, cfg: Optional[List[Dict]] = None):
        """
        Настройка каналов подключения через GRPC

        cfg: Список словарей с настройками

        """
        # Получим список настрок сессии из переданных параметров или считаем из системных настроек
        config: Dict = cfg if cfg else self.__config.get('channels', None)

        if not config:
            raise ValueError("Не заданы настройки каналов gRPC. Проверьте в конфигурации раздел transport.channels")

        for item in config:
            url: str = item.get("url")
            if not url:
                raise ValueError("Не задан url адрес")

            # Если задан SSL сертификат, то создадим для канала полномочия
            certs_filename = item.get("verify")
            credentials = None
            if certs_filename:
                try:
                    with open(certs_filename, 'rb') as f:
                        trusted_certs = f.read()
                    credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
                except (OSError, IOError, EOFError):
                    self.logger.error("Не удалось прочитать SSL сертификат. Будет создан незащищенный канал.")

            # Запомним таймаут, если задан
            self.__timeout = item.get("timeout", TR.SESSION_TIMEOUT)

            # Если есть метаданные, запомним для дальнейшего использования
            self.__metadata.extend(item.get("metadata").items()) if item.get("metadata") else None

            # Создадим gRPC канал
            chanel = grpc.secure_channel(url, credentials) if credentials else grpc.insecure_channel(url)
            self.__channels[item.get("alias").lower()] = chanel

    def setup_stubs(self, cfg: Optional[List[Dict]] = None):
        """
        Настройка Сервисов

        cfg: Список словарей с настройками

        """
        # Получим список настрок сессии из переданных параметров или считаем из системных настроек
        config: Dict = cfg if cfg else self.__config.get('stubs', None)

        if not config:
            raise ValueError("Не заданы настройки Stubs. Проверьте в конфигурации раздел transport.stubs")

        for item in config:
            stub_name = item.get("alias").lower()
            module_name = item.get("module")
            stub_class = item.get("stub")
            if not module_name or not stub_class:
                raise ValueError("Не заданы модуль и имя stub класса")

            # Создадим Stub для каждого канала и добавим его в список
            module = import_module(module_name)
            for chanel_name, chanel in self.__channels.items():
                self.__stubs[(chanel_name, stub_name)] = getattr(module, stub_class)(chanel)

    def execute(self, service_name: str, method_name: str,
                data: Optional[GeneratedProtocolMessageType] = None) -> Optional[GeneratedProtocolMessageType]:
        """
        Выполняет запрос к сервису gRPC

        Args:
            service_name: Наименование сервиса
            method_name: Наименование метода
            data: Передаваемые данные

        Returns:
            Ответ сервиса

        """
        response: Optional[GeneratedProtocolMessageType] = None

        # Запрос будет последовательно выполняться для всех сессий, заданных в конфигурации, до успеха
        for i, (chanel_name, chanel) in enumerate(self.__channels.items()):
            # Попробуем выполнить запрос в рамках сессии, если ошибка то следующей и т.д.
            try:
                log = data if len(str(data)) < MAX_LOG_LENGTH else gzip_data(str(data).encode())
                self.logger.debug(f"Канал: {chanel_name} Сервис: {service_name} Метод: {method_name}\n"
                                  f"Данные: {log}")

                # Проверим наличие вызываемого метода в сконфигурированном stub и вызовем его
                method = getattr(self.__stubs[(chanel_name, service_name)], method_name)
                response = method(request=data, timeout=self.__timeout, metadata=self.__metadata)

                log = response if len(str(response)) < MAX_LOG_LENGTH else gzip_data(str(response).encode())
                self.logger.debug(f"\nОтвет: {log}")

                break

            except grpc.RpcError as e:
                self.logger.exception(f"Ошибка выполнения запроса к gRPC сервису: {str(e)}")
                if i == len(self.__channels) - 1:
                    raise

        return response
