# -*- coding: utf-8 -*-
import logging
from abc import ABC, abstractmethod

from .connection import AbstractConnection


class AbstractConnectionPool(ABC):
    logger: logging.Logger

    @abstractmethod
    def acquire(self) -> AbstractConnection:
        """
        Acquires the connection from pool
        Returns:
            AbstractConnection
        """

    @abstractmethod
    def release(self, connection: AbstractConnection) -> None:
        """
        Closes the connection

        Args:
            connection(AbstractConnection): connection object
        """

    @abstractmethod
    def dispose(self) -> None:
        """
        Dispose pool and free all allocated resources
        """
