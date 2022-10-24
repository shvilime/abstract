import os
import fcntl
import socket
import atexit
import logging
import platform
from typing import Optional

from .utils import abort


class LockError(Exception):
    pass


def lock_socket(name: str, abort_application: Optional[bool] = True) -> socket:
    """
    Блокировка сокета для проверки уникальности запуска. Работает только под Linux

    Args:
        name: Имя, которое будет использовано при привязке сокета
        abort_application: Завершать работу приложения в случае исключения

    Raises:
        NotImplementedError: При попытке вызвать функцию под OS, отличной от Linux
        LockError: Когда приложение уже запущено

    Returns:
        Сокет

    """
    # Блокировка сокетов работает только для Linux
    if platform.system() != "Linux":
        raise NotImplementedError(f"Функционал не работает под {platform.system()}")

    try:
        # Создадим AF_UNIX сокет
        lock: socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Забиндим его в абстрактном пространстве имен (первый байт \0) с полученным именем
        lock.bind(f"\0{name}")
        return lock
    except socket.error as e:
        message: str = f"Приложение уже запущено. {str(e)}"
        logging.warning(message)
        raise LockError if not abort_application else abort(message)


def lock_pid_file(application: str, filename: str, path: Optional[str] = "/tmp",
                  abort_application: Optional[bool] = True):
    """
    Создание и блокировка pid-файла

    Raises:
        LockError: Когда приложение уже запущено

    """

    def unlock(fl: str):
        """
        Разблокировка PID файла
        Args:
            fl: имя файла

        """
        try:
            if fl and os.path.isfile(fl):
                os.remove(fl)
                logging.info("PID файл разблокирован\n")
        except Exception as ex:
            logging.exception(str(ex))

    # Данная реализация блокировки pid файла работает только для Linux
    if platform.system() != "Linux":
        raise NotImplementedError(f"Функционал не работает под {platform.system()}")

    os.makedirs(path, exist_ok=True)
    lock_file_path: str = os.path.join(path, filename)
    logging.info(f"Для блокировки используется файл: {lock_file_path}")

    if os.path.isfile(lock_file_path):
        old_pid: str = open(lock_file_path).read().strip()
        if old_pid and os.path.exists("/proc/%s" % old_pid):
            try:
                cmdline: str = open('/proc/%s/cmdline' % old_pid).read()
                if cmdline and application.lower() in cmdline.lower():
                    message: str = f"Приложение уже запущено {old_pid}"
                    logging.warning(message)
                    raise LockError if not abort_application else abort(message)
            except Exception as e:
                logging.exception(str(e))
                raise LockError if not abort_application else abort(str(e))
        else:
            os.remove(lock_file_path)

    with open(lock_file_path, 'w') as fp:
        try:
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fp.write(str(os.getpid()))
        except (IOError, OSError):
            message: str = f"Не удалось создать файл блокировки {lock_file_path}"
            logging.exception(message)
            raise LockError if not abort_application else abort(message)

    atexit.register(unlock, lock_file_path)
