# -*- coding: utf-8 -*-
import logging
from abc import ABC
from contextlib import contextmanager
from typing import Generator, Any

from .connection import AbstractConnection
from .pool import AbstractConnectionPool
from .transaction import Transaction


class AbstractDAO(ABC):
    """
    Abstract data access object
    """

    def __init__(self, pool: AbstractConnectionPool):
        self._pool: AbstractConnectionPool = pool
        self.logger: logging.Logger = logging.getLogger(__name__)

    @contextmanager
    def acquire(self, auto: bool = False) -> Generator[Transaction, Any, Any]:
        """
        Стартует новую транзакцию и помещает ее в пул транзакций

        Args:
             auto (bool): Если True - автоматический commit или rollback

        Returns:
             Открытая транзакция

        """
        con: AbstractConnection = self._pool.acquire()
        try:
            yield Transaction(con, auto)
        finally:
            self._pool.release(con)
