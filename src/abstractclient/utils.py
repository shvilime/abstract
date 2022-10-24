import os
import re
import sys
import syslog
import logging
import traceback
import subprocess
from gzip import GzipFile
from io import BytesIO
from typing import Optional, Dict

HYPERMARKET: str = "HM"
CONVENIENCE_STORE: str = "CS"
COSMETICS_STORE: str = "SS"
DISTRIBUTION_CENTER: str = "DC"
STORE: str = "MM"
ZOPE: str = "ZOPE"


class LocalDbConf(object):
    __params: Dict
    __ready: bool
    filename: str

    def __init__(self, filename: Optional[str] = "/etc/local_db.conf"):
        self.filename = filename
        self.__params = dict()
        self.__ready = False
        self.__load()

    def __load(self):
        if not os.path.exists(self.filename):
            logging.warning(f"Отсутствует файл {self.filename}")
            return
        try:
            with open(self.filename) as f:
                for line in f:
                    data = re.split(r'\s+', line.strip(), 1)
                    if len(data) == 1:
                        self.__params[data[0]] = None
                    else:
                        self.__params[data[0]] = data[1]

            self.__ready = True

        except (OSError, IOError) as e:
            logging.exception(f"Ошибка при чтении файла {self.filename}. {str(e)}")

    @property
    def ready(self):
        return self.__ready

    def get(self, param: str) -> Optional[str]:
        result: Optional[str] = self.__params.get(param, None)
        if not result:
            logging.warning(f"Не удалось прочитать параметр {param} из {self.filename}")
        return result


def read_hostname() -> str:
    """
    Возвращает название хоста

    Returns:
        Имя хоста

    """
    return subprocess.check_output("hostname", stderr=subprocess.STDOUT, shell=True).decode()


def get_whs_code(filename: Optional[str] = None) -> Optional[str]:
    """
    Определяет код ОО, заданные либо в local_df.conf либо в имени хоста

    Args:
        filename: Опционально, полный путь к файлу с конфигурацией

    Returns:
        Код OO

    """
    db_config = LocalDbConf(filename) if filename else LocalDbConf()
    if db_config.ready:
        code: Optional[str] = db_config.get("code")
    else:
        hostname: str = read_hostname()
        match = re.search(r's([\d]{6})\D*', hostname)
        code: Optional[str] = match.group(1) if match else None

    logging.info(f"Код ОО определен: [{code}]")
    return code


def get_mode() -> Optional[str]:
    """
    Определяет формат ОО, на котором запускается приложения

    Returns:
        Формат ОО

    """
    # Прочитаем формат ОО из переменной окружения. Если переменная окружения не задана, то из имени хоста
    mode: str = os.environ.get("ABSTRACTCLIENT_MODE")
    mode: str = (mode or read_hostname()).upper()

    result: Optional[str] = None

    if any(whs in mode for whs in [CONVENIENCE_STORE, STORE, COSMETICS_STORE]):
        result: str = CONVENIENCE_STORE
    elif any([whs in mode for whs in [HYPERMARKET, ZOPE]]):
        result: str = HYPERMARKET
    elif any([whs in mode for whs in [DISTRIBUTION_CENTER]]):
        result: str = DISTRIBUTION_CENTER

    logging.info(f"Формат ОО определен: [{result}]")
    return result


def log_uncaught_exceptions_hook(*exc_info):
    """
    Функция-Хук для вывода в лог необработанных исключения.
    sys.excepthook = log_uncaught_exceptions_hook

    Args:
        *exc_info: Параметры: класс исключения, экземпляр исключения и объект трассировки
    """
    exc_type, exc_value, exc_traceback = exc_info
    list_tb: list = traceback.extract_tb(exc_traceback)
    # Пробежимся по списку файлов, укоротим имена и очистим от трейсбека PEX bootstrap
    clear_list_tb: list = []
    for tb in list_tb:
        if tb.filename.startswith(".bootstrap"):
            continue
        tb.filename = os.path.join(*tb.filename.split("/")[-2:])
        clear_list_tb.append(tb)

    text = "".join(traceback.format_list(clear_list_tb) + traceback.format_exception_only(exc_type, exc_value))
    logging.critical("Unhandled exception: \n%s", text)


def gzip_data(data: bytes) -> bytes:
    """
    Упаковывает gzip переданный набор данных

    Args:
        data: Данные для упаковки

    Returns:
        Упакованные gzip данные

    """
    gzip_content = BytesIO()
    with GzipFile(fileobj=gzip_content, mode="w") as f:
        f.write(data)

    return gzip_content.getvalue()


def success(message: str, status: Optional[int] = 0):
    """
    Успешное завершение работы c выводом в stdout и syslog
    Args:
        message(str, unicode): сообщение
        status(int): exit-code

    """
    syslog.syslog(message)
    sys.stdout.write(message)
    sys.exit(status)


def abort(message: str, status: Optional[int] = 1):
    """
    Завершение работы с ошибкой c выводом в stderr и syslog
    Args:
        message(str, unicode): сообщение об ошибке
        status(int): exit-code

    """
    message = f"\nОтмена запуска: {message}\n"
    syslog.syslog(message)
    sys.stderr.write(message)
    sys.exit(status)


def warn(message: str):
    """
    Вывод предупреждения в stdout и в syslog
    Args:
        message(str, unicode): сообщение об ошибке

    """
    syslog.syslog(message)
    sys.stdout.write(message)
