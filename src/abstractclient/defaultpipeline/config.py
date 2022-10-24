import importlib
from typing import Optional, Type, Callable, Dict, Any

from .. import environment
from ..abstractpipeline import AbstractConfig
from .transports import HTTPFactory
from .database import DAO, GenericConnectionPool


class DefaultConfig(AbstractConfig):
    """
    Конфигурационный класс. Создает экземпляры переданных классов. Осуществляет настройки всех классов,
    исходя из параметров приложения, заданных в конфигурационном файле. Осуществляет инжектирование
    транспортного класса и класса работы базой данных в репозиторий.

    """
    _transport_cls: Optional[Type]
    _db_cls: Optional[Type]
    _repo_cls: Type

    def __init__(self, repo_cls: Type, db_cls: Optional[Type] = DAO,
                 transport_cls: Optional[Type] = HTTPFactory) -> None:
        """
        Args:
            transport_cls: Тип абстрактного класса Transport
            db_cls: Тип абстрактного класса Database
            repo_cls: Тип абстрактного класса Repository
        """
        self._repo_cls = repo_cls
        self._db_cls = db_cls
        self._transport_cls = transport_cls

    def database(self) -> Dict[str, Any]:
        """
        Инициализация AbstractFactory класса для работы с Database

        Returns:
            Словарь с набором экземпляров класса db_cls, переданного в конфигуратор

        """
        environment.logger.info("Инициализация подключения к БД")
        databases: Dict[str, Any] = {}

        # Получим список настрое для транспортных систем
        if not hasattr(environment, 'DATABASE'):
            raise ValueError("Не заданы настройки баз данных. Проверьте в конфигурации раздел DATABASE")

        for key, db in environment.DATABASE.items():
            # Получим настройки подключения
            if not hasattr(db, 'credentials'):
                raise ValueError(f"В настройках базы '{key}' отсутствует раздел credentials")

            # Получим настройки пула подключений
            if not hasattr(db, 'pool'):
                raise ValueError(f"В настройках базы '{key}' отсутствует раздел pool")

            # Получим фабрику подключения
            if not hasattr(db, 'connection'):
                raise ValueError(f"В настройках базы '{key}' отсутствует раздел connection")
            # Импортируем фабрику коннектов
            module: str = importlib.import_module(db.connection.get("module"))
            connection_fabric: Callable = getattr(module, db.connection.get("function", "connect"))

            pool: GenericConnectionPool = GenericConnectionPool(
                connection_fabric,
                db.credentials,
                db.pool.pool_size,
                db.pool.max_overflow,
                db.pool.timeout,
                db.pool.use_lifo
            )

            databases[key] = self._db_cls(pool)

        return databases

    def transport(self) -> Dict[str, Any]:
        """
        Инициализация AbstractFactory класса для работы с HTTP

        Returns:
            Словарь с набором экземпляров класса transport_cls, заданных в настройках конфигуратора

        """
        environment.logger.info("Инициализация подключения к ГК")

        # Получим список настрое для транспортных систем
        if not hasattr(environment, 'TRANSPORT'):
            raise ValueError("Не заданы настройки транспортных систем. Проверьте в конфигурации раздел TRANSPORT")

        transports: Dict[str, Any] = {}
        for key, connect in environment.TRANSPORT.items():
            transports[key] = self._transport_cls(connect)

        return transports

    def repository(self) -> Any:
        """
        Инициализация AbstractRepository класса для работы с бизнес-логикой приложения

        Returns:
            Any: Экземпляр класса repo_cls, переданного в конфигуратор

        """
        environment.logger.info("Инициализация репозитория бизнес-логики")

        http: Dict[str, Any] = self.transport()
        db: Dict[str, Any] = self.database()

        return self._repo_cls(db=db, transport=http)


class ApplicationContext:
    """
    Основной класс для инициализации injections
    """
    cfg: AbstractConfig = None

    def __init__(self, configuration: AbstractConfig) -> None:
        self.cfg = configuration

    def get_dependency(self, name: str, expected_type: Type) -> Any:
        """
        Args:
            name: Наименование метода, который будет вызываться из класса DefaultConfig
            expected_type: Ожидаемый тип класса, который должен быть получен в результате

        Returns:
            Any: Экземпляр класса, запрошенного из DefaultConfig
        """
        # Получим экземпляр класса, переданного в name из конфигуратора DefaultConfig
        dependency: Any = getattr(self.cfg, name)()
        # Если тип полученного экземпляра не будет соответствует ожидаемому классу
        if not isinstance(dependency, expected_type):
            raise TypeError("Использован не верный класс объекта")

        return dependency
