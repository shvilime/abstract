# -*- coding: utf-8 -*-
import json
import logging
from dataclasses import make_dataclass, asdict
from uuid import uuid4
from abc import ABC, abstractmethod
from typing import Type, Union, Iterable, Dict, List, Mapping, Any, Optional

from .exceptions import DatabaseError, ProgrammingError, InterfaceError, DataError, OperationalError, \
    IntegrityError, InternalError, NotSupportedError
from .connection import AbstractConnection
from .cursor import AbstractCursor
from .utils import GenericJSONEncoder
from ..utils import gzip_data
from .. import environment

MAX_DB_ANSWER_LENGTH: int = environment.get("MAX_LOG_LENGTH", 5000)
MAPPING_CLS_NAME: str = "DBMapping"
DBMap = Type[MAPPING_CLS_NAME]


class FetchStrategy(ABC):
    """
    Базовый режим выборки
    """

    def __init__(self, cursor):
        self.cursor = cursor

    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Считать данные из курсора по заданной стратегии
        """


class FetchAll(FetchStrategy):
    """
    Выбрать все
    """

    def execute(self) -> List[DBMap]:
        """
        Считать все данные из курсора
        """
        result: List[Any] = self.cursor.fetchall()

        if not len(result):
            return result

        cls = make_model_class(self.cursor.description)
        return [cls(**{col[0].lower(): row[idx] for idx, col in enumerate(self.cursor.description)}) for row in result]


class FetchNone(FetchStrategy):
    """
    Без возвращаемого значения
    """

    def execute(self) -> List:
        """
        Не считывать данные из курсора
        """
        return []


class FetchOne(FetchStrategy):
    """
    Выбрать одно значение
    """

    def execute(self) -> Optional[DBMap]:
        """
        Считать одну строку из курсора
        """
        result: Any = self.cursor.fetchone()

        if not result:
            return result

        cls = make_model_class(self.cursor.description)
        return cls(**{col[0].lower(): result[idx] for idx, col in enumerate(self.cursor.description)})


def pretty_log(dataset: Optional[Union[Iterable[DBMap], DBMap]] = None) -> Union[str, bytes]:
    """
    Форматирование результата транзакции

    Args:
        dataset: логируемые данные
    """
    if not dataset:
        return "\nQuery result is:\nNo data\n"

    data = [row.asdict() for row in dataset] if isinstance(dataset, list) else dataset.asdict()
    result = json.dumps(data, indent=4, ensure_ascii=False, cls=GenericJSONEncoder)

    # Если результат больше параметра MAX_DB_ANSWER_LENGTH, то быстренько пожмем его gzip
    if len(result) > MAX_DB_ANSWER_LENGTH:
        result = gzip_data(result.encode())
    # Если результат все еще велик, то просто выведем информацию о настройке в конфиге - MAX_LOG_LENGTH
    if len(result) > MAX_DB_ANSWER_LENGTH:
        result = f"To long for logging. Please, set or increase param MAX_LOG_LENGTH (current {MAX_DB_ANSWER_LENGTH}b.)"

    return f"\nQuery result is:\n{result}\n"


def make_model_class(dataset_item: Mapping):
    """
    Конвертер маппинга в датакласс

    Args:
        dataset_item(Mapping): маппинг
    """
    return make_dataclass(
        MAPPING_CLS_NAME,
        [(val[0].lower(), val[1]) for val in dataset_item],
        frozen=True,
        namespace={
            "asdict": lambda self: asdict(self)
        }
    )


various_excps = {
    'DatabaseError': DatabaseError,
    'ProgrammingError': ProgrammingError,
    'InterfaceError': InterfaceError,
    'DataError': DataError,
    'OperationalError:': OperationalError,
    'IntegrityError': IntegrityError,
    'InternalError': InternalError,
    'NotSupportedError': NotSupportedError
}


def union_exception(e: Exception):
    return various_excps.get(e.__class__.__name__)


class Transaction:
    ONE = FetchOne
    NOTHING = FetchNone
    MANY = FetchAll

    def __init__(self, con: AbstractConnection, auto: bool = False):
        self._con: AbstractConnection = con
        self.__guid: str = uuid4().hex
        self.auto: bool = auto
        self.logger: logging.Logger = logging.getLogger(__name__)

    def callproc(
            self,
            statement: str,
            params: Optional[Union[Iterable, Dict]] = None,
            fetch: Type[FetchStrategy] = FetchAll
    ) -> Optional[Union[Iterable[DBMap], DBMap]]:
        """
        Call a stored database procedure with the given name.

        Args:
            statement (str): procedure name
            params (Union[Tuple, List]): bind params
            fetch (Type[FetchStrategy]): fetch mode

        Returns:
            Optional[Union[Iterable[DataModel], DataModel]]
        """
        cursor: AbstractCursor = self.start(statement, params or ())
        try:
            cursor.callproc(statement, params)
        except Exception as e:
            ex = union_exception(e)
            raise ex(str(e)) if ex else e
        return self.fetch(cursor, fetch)

    def execute(
            self,
            statement: str,
            params: Optional[Union[Iterable, Dict]] = None,
            fetch: Type[FetchStrategy] = FetchAll
    ) -> Optional[Union[Iterable[DBMap], DBMap]]:
        """
        Prepare and execute a database operation (query or command).

        Args:
            statement (str): SQL statement
            params (Union[Tuple, List]): bind params
            fetch (Type[FetchStrategy]): fetch mode

        Returns:
            Optional[Union[Iterable[DataModel], DataModel]]
        """
        cursor: AbstractCursor = self.start(statement, params or ())
        try:
            cursor.execute(statement, params)
        except Exception as e:
            ex = union_exception(e)
            raise ex(str(e)) if ex else e

        return self.fetch(cursor, fetch)

    def executemany(
            self,
            statement: str,
            params: Union[Iterable[Dict], Iterable[Iterable]],
            fetch: Type[FetchStrategy] = FetchAll
    ) -> Optional[Union[Iterable[DBMap], DBMap]]:
        """
        Prepare a database operation (query or command) and then execute it against all
        parameter sequences or mappings found in the sequence.

        Args:
            statement (str): SQL statement
            params (Union[Iterable[Dict], Iterable[Iterable]]): bind params
            fetch (Type[FetchStrategy]): fetch mode

        Returns:
            Optional[Union[Iterable[DataModel], DataModel]]
        """
        cursor: AbstractCursor = self.start(statement, params or ())
        try:
            cursor.executemany(statement, params)
        except Exception as e:
            ex = union_exception(e)
            raise ex(str(e)) if ex else e
        return self.fetch(cursor, fetch)

    def start(self, statement: str, params: Optional[Union[Iterable, Dict]] = None):
        """
        Open cursor

        Args:
            statement (str): SQL statement
            params (Union[Tuple, List]): bind params
        """
        cur: AbstractCursor = self._con.cursor()

        if not params:
            params = ()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.log(logging.DEBUG, f"\nRunning SQL query:\n{statement}\nwith params: {str(params)}\n")

        return cur

    def fetch(self, cursor: AbstractCursor, fetch: Type[FetchStrategy] = FetchAll):
        """
        Fetch results

        Args:
            cursor(AbstractCursor): cursor
            fetch(Type[FetchStrategy]): fetch mode

        Returns:
            Optional[Union[Iterable[DataModel], DataModel]]
        """
        try:
            res: Optional[Union[Iterable[DBMap], DBMap]] = fetch(cursor).execute()
        except Exception as e:
            if self.auto:
                self._con.rollback()
            ex = union_exception(e)
            raise ex(str(e)) if ex else e
        finally:
            cursor.close()

        if self.auto:
            self._con.commit()

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.log(logging.DEBUG, pretty_log(res))

        return res

    def commit(self):
        """
        Коммит транзакции
        """
        self._con.commit()

    def rollback(self):
        """
        Откат транзакции
        """
        self._con.rollback()
