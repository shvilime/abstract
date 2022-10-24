# -*- coding: utf-8 -*-
import os
import sys
import json
import toml
import locale
import socket
import logging
import logging.config
from dynaconf import LazySettings
from typing import List, Dict

from .utils import LocalDbConf, abort, log_uncaught_exceptions_hook, get_mode, get_whs_code
from .locker import lock_socket, lock_pid_file
from .onlinemm import get_info


class Environment(LazySettings):
    logger: logging.Logger = logging.getLogger("abstractclient")
    lock: socket

    def __init__(self):
        super().__init__()
        # Вызовем утилиты для вспомогательных настроек приложения: Logger, Dirs, Environment, WHS, DB, PID
        self.__check_application_name()
        self.__create_dirs()
        self.__setup_logger()
        if self.get("SINGLE_INSTANCE", True):
            self.__lock_pid_file()
            self.__lock_socket()
        self.__check_encoding()
        self.__local_db_conf_ext()
        self.__get_whs_code()
        self.__get_mode()

    def __check_application_name(self):
        """
        Проверка наличия имени приложения в настройках

        """
        if not hasattr(self, 'APPLICATION'):
            message: str = 'В настройках приложения не задано значение переменной APPLICATION'
            self.logger.error(message)
            abort(message)

    def __setup_logger(self):
        """
        Инициализация логгера

        """
        if not hasattr(self, "LOGGING"):
            abort("Задайте в настройках пусть к файлу с конфигурацией Logger")

        if not os.path.exists(self.LOGGING):
            abort(f"{self.LOGGING} не найден.")

        filename, file_extension = os.path.splitext(self.LOGGING)
        parser: Dict = {
            ".json": json.load,
            ".toml": toml.load
        }
        with open(self.LOGGING) as f:
            logging.config.dictConfig(parser.get(file_extension)(f))

    def __lock_socket(self):
        """
        Блокировка сокета для проверки уникальности запуска фреймворка

        """
        try:
            self.lock = lock_socket(self.APPLICATION)
        except NotImplementedError:
            return

    def __lock_pid_file(self):
        """
        Создание и блокировка pid-файла

        """
        try:
            lock_pid_file(
                application=self.APPLICATION,
                filename=f"{self.APPLICATION.lower()}.pid",
                path=self.get('PID_FILE_PATH', '/tmp')
            )
        except NotImplementedError:
            return

    def __check_encoding(self):
        """
        Функция проверки наличия переменных окружения, отвечающих за перекодировку
        """
        lang: str = locale.getdefaultlocale()[0]
        encoding: str = locale.getpreferredencoding(False)

        environments = {'LC_ALL': f'{lang}.{encoding}',
                        'LC_CTYPE': f'{lang}.{encoding}',
                        'PYTHONIOENCODING': 'UTF-8'}
        # Если инкодинг не UTF-8 и не заданы перечисленные переменные окружения - ругаемся и выходим
        if encoding != "UTF-8" \
                and not all([os.environ.get(key) == value for key, value in environments.items()]):
            formatted_env: List = [f'\t{key}={value} [{os.environ.get(key)}]\n' for key, value in environments.items()]
            message: str = f"Задайте в переменных окружения все значения {formatted_env}"
            self.logger.error(message)
            abort(message)

    def __local_db_conf_ext(self):
        """
        Загрузка параметров подключения к базе данных firebird на ОО

        """
        # Так как возможна альтернатива получения конфига БД в виде config_oo.toml
        # Данный метод перестает быть обязательным. Если в настройках не указан
        # LOCAL_DB_CONF_PATH - ничего не делаем
        if not self.get("LOCAL_DB_CONF_PATH"):
            return

        # Загрузим конфиг
        conf = LocalDbConf(self.get("LOCAL_DB_CONF_PATH"))
        if not conf.ready:
            return

        # Прочитаем и запишем в настройки для коннекта к базам, если они не заполнены
        try:
            for name, db in self.DATABASE.items():
                if not db.credentials.get('dsn'):
                    db.credentials.dsn = conf.get("connection")
                if not db.credentials.get("user"):
                    db.credentials.user = conf.get("user")
                if not db.credentials.get("password"):
                    db.credentials.password = conf.get("password")
        except (KeyError, AttributeError) as e:
            self.logger.error(str(e))
            abort(str(e))

    def __get_whs_code(self):
        """
        Определение кода ОО

        """
        if not self.get("WHSCODE"):
            self.WHSCODE = get_whs_code(self.get("LOCAL_DB_CONF_PATH"))

    def __get_mode(self):
        """
        Определение типа ОО

        """
        self.MODE = get_mode()

        # Если не сработало стандартное определение типа ОО, запросим информацию в сервисе onlinemm
        if not self.MODE:
            self.MODE = get_info(self.get("TRANSPORT", {}).get("onlinemm", {}), self.WHSCODE).type
            self.logger.info(f"Формат ОО определен: [{self.MODE}]")

        if not self.MODE:
            message: str = """Неизвестный формат ОО. Работа приложения будет завершена.\n
                              Можно задать формат ОО в переменной окружения ABSTRACTCLIENT_MODE"""
            self.logger.error(message)
            abort(message)

    def __create_dirs(self):
        """
        Считывает из конфигурации [main][auto_create_directory] и создает перечисленные каталоги

        """
        if not hasattr(self, 'AUTO_CREATE_DIRECTORY'):
            return

        for path in self.AUTO_CREATE_DIRECTORY:
            try:
                os.makedirs(path, exist_ok=True)
            except OSError as e:
                self.logger.exception(f"Не удалось создать для работы директорию {path}\n{str(e)}")


# Загрузим настройки
__env: str = os.environ.get('ENV_FOR_DYNACONF')
if not __env:
    abort("Не задана переменная окружения ENV_FOR_DYNACONF - [development, production, staging].")
environment = Environment()

# Установим hook для логирования необработанных ошибок
sys.excepthook = log_uncaught_exceptions_hook
