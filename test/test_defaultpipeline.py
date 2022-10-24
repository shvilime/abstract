import os
import json
import pytest

from src.abstractclient.defaultpipeline.config import DefaultConfig
from src.abstractclient.abstractpipeline import AbstractRepository


class JustTest(AbstractRepository):
    @staticmethod
    def run():
        return "OK"


@pytest.fixture(scope="module")
def repo():
    # Создадим конфигуратор и передадим ему тип класса Репозитория
    config_object = DefaultConfig(repo_cls=JustTest)
    return config_object.repository()


def test_transport_factory(repo):
    """
    Тест Фабрики коннектов к шине TransportFactory
    """
    response = repo.transport['headquarter'].execute("get",
                                                     json_data='{"test": "ok"}',
                                                     dynamic_values={
                                                         "whscode": "999999",
                                                         "msg_id": "333"
                                                     },
                                                     test="value1")
    assert response.get("origin").translate({ord(i): None for i in '., '}).isdigit()


def test_db_connection_with_transaction(repo):
    """
    Тест клиента DatabaseFactory с пулом транзакций и получением одной записи
    """
    with open(os.path.dirname(os.path.abspath(__file__)) + "/sql.json", "r") as file:
        sql_json = json.load(file)
        this_test_sql = sql_json.get("test_db_connection_with_transaction")

    for key, sentence in this_test_sql.items():
        with repo.database['firebird'].acquire(True) as tr:
            row = tr.execute(sentence['sql'], fetch=tr.ONE)
            assert getattr(row, sentence['field'].lower()) == sentence['result']


def test_db_connection_non_transaction(repo):
    """
    Тест клиента DatabaseFactory без транзакции
    """
    with open(os.path.dirname(os.path.abspath(__file__)) + "/sql.json", "r") as file:
        sql_json = json.load(file)
        this_test_sql = sql_json.get("test_db_connection_non_transaction")

    for key, sentence in this_test_sql.items():
        with repo.database['firebird'].acquire(True) as tr:
            row = tr.execute(sentence['sql'], fetch=tr.ONE)
            assert getattr(row, sentence['field'].lower()) == "RUB"


def test_dependency(repo):
    """
    Тест вызова метода
    """
    assert repo("run") == "OK"
