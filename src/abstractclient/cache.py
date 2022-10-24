import os
import pickle
import time
from threading import Thread
from typing import Dict, Optional, Any, ItemsView, Hashable


class CacheFileException(Exception):
    """ Ошибка при работе с файлом кеша на диске """


class PickledCacheFile(object):
    __filename: str
    __relevance: int
    __db: Dict
    __auto: bool
    __protocol: int
    __thread: Thread

    def __init__(
            self,
            cache_filename: str,
            relevance: Optional[int] = 0,
            auto: Optional[bool] = True,
            pickle_protocol: Optional[int] = 3  # Default version for Python 3.0 - 3.7
    ):
        self.__filename = cache_filename
        self.__relevance = relevance
        self.__db = dict()
        self.__auto = auto
        self.__protocol = pickle_protocol
        self.__unpickle()

    def __unpickle(self):
        """
        Расконсервирует словарик __db из файла

        """
        if self.actual():
            try:
                with open(self.__filename, 'rb') as file:
                    data: bytes = file.read()
                self.__db = pickle.loads(data, fix_imports=True)
            except (OSError, IOError, EOFError, pickle.PickleError):
                raise CacheFileException

    def __pickle(self):
        """
        Консервирует в файл словарик __db

        """
        try:
            with open(self.__filename, 'wb') as file:
                pickle.dump(self.__db, file, protocol=self.__protocol)
        except (OSError, IOError, pickle.PicklingError):
            raise CacheFileException

    def actual(self) -> bool:
        result: bool = False

        if os.path.exists(self.__filename):
            if not self.__relevance:
                return True
            if time.time() - os.path.getmtime(self.__filename) < self.__relevance:
                result = True

        return result

    def dump(self):
        """
        Запускает поток, который консервирует данные в файл

        """
        os.makedirs(os.path.dirname(self.__filename), exist_ok=True)
        self.__thread = Thread(
            target=self.__pickle
        )
        self.__thread.start()
        self.__thread.join()

    def set(self, key: Hashable, value: Any):
        """
        Записывает в хранилище значение по ключу

        Args:
            key: Ключи
            value: Значение

        """
        self.__db[key] = value
        self.dump() if self.__auto else None

    def get(self, key: Hashable, default: Optional[Any] = None) -> Optional[Any]:
        """
        Возвращает из хранилища значение по ключу

        Args:
            key: Ключ
            default: Дефолтное значение, если ключ отсутствует

        Returns:
            Значение

        """
        try:
            return self.__db[key]
        except KeyError:
            return default

    def rem(self, key: Hashable) -> bool:
        """
        Удаляет по ключу данные из хранилища

        Args:
            key: Ключ

        Returns:
            Результат удаления

        """
        if key not in self.__db:
            return False
        self.__db.pop(key, None)
        self.dump() if self.__auto else None
        return True

    def items(self) -> ItemsView:
        """
        Возвращает список данных хранилища

        Returns:
            Представление хранилища

        """
        return self.__db.items()
