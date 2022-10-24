import os
import pytest
import threading

from src.abstractclient.cache import PickledCacheFile, CacheFileException


@pytest.fixture(scope="session")
def cache_file(tmp_path_factory):
    return tmp_path_factory.mktemp("data") / "cache.pickle"


@pytest.fixture(scope="session")
def cache(cache_file):
    yield PickledCacheFile(cache_file)


def test_cache_get_none_key(cache):
    assert cache.get("empty") is None


def test_write_in_threads(cache):
    num_threads: int = 100
    threads: list = []
    # Запишем значения в несколько потоков
    for count in range(0, num_threads):
        threads.append(
            threading.Thread(
                target=cache.set, args=(count, f"value{count}")
            )
        )
    for t in threads:
        t.start()
        t.join()

    # Проверим записанные значения
    for count in range(0, num_threads):
        assert cache.get(count) == f"value{count}"


def test_broken_cache_file(cache_file):
    # Испортим файл кеша
    with open(cache_file, 'wb') as file:
        file.write("".encode())
    # Должна вернуться ошибка
    with pytest.raises(CacheFileException):
        PickledCacheFile(cache_file)
    # Удалим испорченный файл
    os.remove(cache_file)
