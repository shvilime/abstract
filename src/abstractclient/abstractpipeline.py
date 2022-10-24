import logging
import threading
from abc import abstractmethod, ABC
from contextlib import contextmanager
from requests import Response

from typing import Callable, Dict, Tuple, NoReturn, Any, Optional
from .utils import abort


class AbstractConnectionPool(ABC):
    connection_fabric: Callable = None
    params: Dict = None
    _overflow: int = 0
    _max_overflow: int = 0
    _timeout: int = 20
    _overflow_lock: threading.Lock = threading.Lock()
    suppressed_exc: Tuple = ()

    @abstractmethod
    def acquire(self, *args, **kwargs) -> NoReturn:
        pass

    @abstractmethod
    def release(self, *args, **kwargs) -> NoReturn:
        pass

    @abstractmethod
    def dispose(self, *args, **kwargs) -> NoReturn:
        pass


class AbstractFactory(ABC):
    logger: logging.Logger = None
    _pool: AbstractConnectionPool = None

    @contextmanager
    def acquire(self) -> object:
        con: AbstractConnectionPool = self._pool.acquire()
        try:
            yield con
        finally:
            self._pool.release(con)


class AbstractConfig(ABC):
    """
    Абстрактный класс Конфигуратора
    Для первичной инициализации классов DB, HTTP, Repo
    """

    @abstractmethod
    def database(self) -> AbstractFactory:
        pass

    @abstractmethod
    def transport(self) -> AbstractFactory:
        pass

    @abstractmethod
    def repository(self) -> object:
        pass


class AbstractRepository(ABC):
    """
    Абстрактный класс Репозитория.
    Хранит и управляет классами для работы с HTTP - transport, DB - database
    """
    logger: logging.Logger = None               #: Логгер
    database: Dict[str, AbstractFactory] = {}   #: словарь с экземлярами класса, для работы с базой данных
    transport: Dict[str, AbstractFactory] = {}  #: Словарь экземпляров класса, для работы с транспортной системой

    def __init__(self, db: Dict[str, AbstractFactory], transport: Dict[str, AbstractFactory]) -> None:
        self.logger = logging.getLogger(__name__)
        self.database = db
        self.transport = transport

    def __call__(self, attr: str) -> Any:
        if not hasattr(self, attr):
            abort("Используется неизвестный метод репозитория")

        method: Any = getattr(self, attr)

        if not callable(method):
            abort("Используется неправильный метод репозитория")

        try:
            return method()
        except Exception as e:
            message: str = f"Ошибка при выполнении метода {method}: {e}"
            self.logger.exception(message)
            abort(message)


class ExtractStrategy(ABC):
    """
    Абстрактный класс Метода извлечения данных из ответа HTTP сервера.
    """
    logger: logging.Logger = None               #: Логгер

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def extract(self, response: Response, code: Optional[str] = None):
        """
        Парсинг тела HTTP запроса
        """
