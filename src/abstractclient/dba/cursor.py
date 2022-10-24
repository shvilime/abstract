# -*- coding: utf-8 -*-
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, TypeVar, Dict, Iterable, Union
from datetime import date, time, datetime


class ColumnType(Enum):
    Date = TypeVar("Date", bound=date)
    Time = TypeVar("Time", bound=time)
    Timestamp = TypeVar("Timestamp", bound=float)
    DateFromTicks = TypeVar("DateFromTicks", bound=date)
    TimeFromTicks = TypeVar("TimeFromTicks", bound=time)
    TimestampFromTicks = TypeVar("TimestampFromTicks", bound=float)
    Binary = TypeVar("Binary", bound=bytes)
    STRING = TypeVar("STRING", bound=str)
    BINARY = TypeVar("BINARY", bound=bytes)
    NUMBER = TypeVar("NUMBER", bound=int)
    DATETIME = TypeVar("DATETIME", bound=datetime)
    ROWID = TypeVar("ROWID", bound=int)


@dataclass(frozen=True)
class Metadata:
    name: str
    type_code: ColumnType
    display_size: Optional[int] = None
    internal_size: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    null_ok: Optional[bool] = None


class AbstractCursor(ABC):

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """
        Logger

        Returns:
            logging.Logger
        """

    @property
    @abstractmethod
    def description(self) -> Metadata:
        """
        This read-only attribute is a sequence of 7-item sequences.

        Returns:
            Metadata
        """

    @property
    @abstractmethod
    def rowcount(self) -> int:
        """
        This read-only attribute specifies the number of rows that the last query produced or affected
        Returns:
            int
        """

    @property
    @abstractmethod
    def arraysize(self) -> int:
        """
        This read/write attribute specifies the number of rows to fetch at a time with .fetchmany().
        It defaults to 1 meaning to fetch a single row at a time.
        Returns:
            int
        """

    @arraysize.setter
    @abstractmethod
    def arraysize(self, value: int):
        """
        Setter for arraysize
        """

    @abstractmethod
    def setinputsizes(self, sizes: Iterable[ColumnType]):
        """
        This can be used before a call to .execute*() to predefine memory areas for the operation's parameters.
        """

    @abstractmethod
    def setoutputsize(self, size: ColumnType, column_index: Optional[int] = None):
        """
        Set a column buffer size for fetches of large columns (e.g. LONGs, BLOBs, etc.).
        The column is specified as an index into the result sequence.
        Not specifying the column will set the default size for all large columns in the cursor.
        """

    @abstractmethod
    def callproc(self, name: str, parameters: Optional[Union[Iterable, Dict]]) -> None:
        """
        Call a stored database procedure with the given name.
        The sequence of parameters must contain one entry for each argument that the procedure expects.
        The result of the call is returned as modified copy of the input sequence.
        Input parameters are left untouched, output and input/output parameters replaced with possibly new values.
        """

    @abstractmethod
    def close(self) -> None:
        """
        Close the cursor now
        """

    @abstractmethod
    def execute(self, name: str, parameters: Optional[Union[Iterable, Dict]]) -> None:
        """
        Prepare and execute a database operation (query or command).
        Parameters may be provided as sequence or mapping and will be bound to variables in the operation.
        """

    @abstractmethod
    def executemany(self, name: str, parameters: Iterable[Union[Iterable, Dict]]) -> None:
        """
        Prepare a database operation (query or command) and then execute it against all parameter sequences or mappings
        """

    @abstractmethod
    def fetchone(self) -> Dict:
        """
        Fetch the next row of a query result set, returning a single sequence, or None when no more data is available.
        """

    @abstractmethod
    def fetchmany(self) -> Iterable[Dict]:
        """
        Fetch the next set of rows of a query result, returning a sequence of sequences (e.g. a list of tuples).
        An empty sequence is returned when no more rows are available.
        """

    @abstractmethod
    def fetchall(self) -> Iterable[Dict]:
        """
        Fetch all (remaining) rows of a query result, returning them as a sequence of sequences (e.g. a list of tuples).
        Note that the cursor's arraysize attribute can affect the performance of this operation.
        """

    @abstractmethod
    def nextset(self) -> Iterable[Dict]:
        """
        This method will make the cursor skip to the next available set,
        discarding any remaining rows from the current set.
        """
