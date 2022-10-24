import pytest
from src.abstractclient.locker import LockError, lock_pid_file, lock_socket


def test_locker_socket():
    """
    Тест создания локера с помощью сокет
    """
    try:
        lock = lock_socket("abstractclient")
        if lock:
            with pytest.raises(LockError):
                lock_socket("abstractclient", abort_application=False)
    except NotImplementedError:
        return


def test_locker_pid_file():
    """
    Тест создания локера с pid файла
    """
    try:
        lock_pid_file("test", "test.pid", "/tmp")
        with pytest.raises(LockError):
            lock_pid_file("test", "test.pid", "/tmp", abort_application=False)
    except NotImplementedError:
        return
