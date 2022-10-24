# -*- coding: utf-8 -*-


import logging
from abc import abstractmethod, ABC

from .cursor import AbstractCursor


class AbstractConnection(ABC):
    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """
        Logger

        Returns:
            logging.Logger
        """

    @abstractmethod
    def commit(self, *args, **kwargs):
        """
        Commit any pending transaction to the database.
        """

    @abstractmethod
    def close(self, *args, **kwargs):
        """
        Close the connection now
        """

    @abstractmethod
    def rollback(self, *args, **kwargs) -> None:
        """
        In case a database does provide transactions
        this method causes the database to roll back to the start of any pending transaction.
        """

    @abstractmethod
    def cursor(self, *args, **kwargs) -> AbstractCursor:
        """
        Return a new Cursor Object using the connection.
        """
