# -*- coding: utf-8 -*-
"""
Модуль, описывающий иерархию классов взаимодействия с базой данных.
Для открытия подключения достаточно создать инстанс DBAdapter
DI протестирован с fdb, kinterbasdb, cx_Oracle.
Нужно протестировать psycopg.
"""
import logging
import threading

from queue import LifoQueue, Queue
from typing import Callable, Union, Type, Iterable, Optional

from ..dba.pool import AbstractConnectionPool
from ..dba.dao import AbstractDAO
from ..dba.transaction import union_exception


class GenericConnectionPool(AbstractConnectionPool):

    def __init__(self, connection_fabric: Callable, credentials: dict, pool_size: int = 5, max_overflow: int = 10,
                 timeout: int = 30, use_lifo: bool = False, suppressed_exc: Optional[Iterable[Type]] = None):
        """
        Универсальный пул подключений к БД

        Args:
            connection_fabric(Callable): фабрика подключений к БД
            credentials(dict): данные для подключения
            pool_size(int): верхняя граница пула подключений
            max_overflow(int): максимальное допустимое переполнение
            timeout(int): время ожидание свободного подключения
            use_lifo(bool): использовать стек вместо очереди
            suppressed_exc(Optional[Iterable[Type]]): игнорируемые исключения
        """
        self.connection_fabric: Callable = connection_fabric
        self.credentials: dict = credentials
        self._pool: Union[LifoQueue, Queue] = LifoQueue(maxsize=pool_size) if use_lifo else Queue(maxsize=pool_size)
        self._overflow: int = 0 - pool_size
        self._max_overflow: int = max_overflow
        self._timeout: int = timeout
        self._overflow_lock: threading.Lock = threading.Lock()
        self.suppressed_exc: Iterable[Type] = () if suppressed_exc is None else suppressed_exc
        self.logger: logging.Logger = logging.getLogger()

    def release(self, conn):
        """
        Вернуть подключение в пул
        Args:
            conn: подключение
        """
        if not self._pool.full():
            self._pool.put(conn, False)

        try:
            conn.close()
        except self.suppressed_exc as e:
            self.logger.warning(f"Проигнорировано исключение при закрытии подключения: {e}")
        except Exception as e:
            self._dec_overflow()
            ex = union_exception(e)
            raise ex(str(e)) if ex else e

        self._dec_overflow()

    def acquire(self) -> object:
        """
        Получить подключение
        """
        use_overflow = self._max_overflow > -1
        wait = use_overflow and self._overflow >= self._max_overflow

        if use_overflow and self._overflow >= self._max_overflow:
            if not wait:
                return self.acquire()

            raise OverflowError("Connection pool overflow")

        if self._inc_overflow():
            try:
                return self.connection_fabric(**self.credentials)
            except Exception as e:
                self._dec_overflow()
                ex = union_exception(e)
                raise ex(str(e)) if ex else e

        # теоретически, если один поток получил лок в _inc_overflow, и другой поток пришел следом и ждет
        # когда лок освободится, то, когда первый поток освободит лок,
        # то второй может выполниться быстрее чем первый и забрать подключение из пула раньше,
        # тогда, если в пуле не осталось подключений первый поток будет вынужден ждать появления коннекта в пуле
        return self._pool.get()

    def _inc_overflow(self) -> bool:
        """
        Увеличить счетчик открытых подключений

        Returns:
            bool
        """
        if self._max_overflow == -1:
            self._overflow += 1
            return True

        with self._overflow_lock:
            if self._overflow < self._max_overflow:
                self._overflow += 1
                return True
            else:
                return False

    def _dec_overflow(self) -> bool:
        """
        Уменьшить счетчик открытых подключений

        Returns:
            bool
        """
        if self._max_overflow == -1:
            self._overflow -= 1
            return True
        with self._overflow_lock:
            self._overflow -= 1
            return True

    def dispose(self) -> None:
        """
        Закрыть пул
        """
        while not self._pool.empty():
            self._pool.get_nowait().close()

        self._overflow = 0 - self.size

    def status(self) -> str:
        """
        Текущий статус пула
        Returns:
            tuple
        """
        return ("Pool size: %d  Connections in _pool: %d\n Current Overflow: %d Current Checked out\n connections: %d"
                % (self.size, self.checkedin, self.overflow, self.checkedout))

    @property
    def size(self) -> int:
        """
        Размерность пула
        Returns:
            int
        """
        return self._pool.maxsize

    @property
    def timeout(self) -> int:
        """
        Время ожидания запроса
        Returns:
            int
        """
        return self._timeout

    @property
    def checkedin(self) -> int:
        """
        Кол-во оставшихся подключений
        Returns:
            int
        """
        return self._pool.qsize()

    @property
    def overflow(self) -> int:
        """
        Граница переполнения
        Returns:
            int
        """
        return self._overflow

    @property
    def checkedout(self) -> int:
        """
        Кол-во занятых подключений
        Returns:
            int
        """
        return self._pool.maxsize - self._pool.qsize() + self._overflow

    def test_acquire(self, username: str, password: str):
        """
        Метод для попытки авторизации в БД под любым пользователем,
        создан для обратной совместимости с существующим алгоритмом аторизации в tsdserver.
        Удалить, как только алгоритм изменится.

        Args:
            username: логин
            password: пароль
        """
        credentials: dict = self.credentials.copy()
        credentials.update({
            "user": username,
            "password": password
        })
        return self.connection_fabric(**credentials)


class DAO(AbstractDAO):
    """
    Database adapter
    """
    _pool: GenericConnectionPool
