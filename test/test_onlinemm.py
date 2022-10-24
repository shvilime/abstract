from src.abstractclient import environment
from src.abstractclient.onlinemm import get_info


def test_onlinemm():
    """
    Проверка работы c сервисом onlinemm
    """
    assert get_info(environment.TRANSPORT.onlinemm, environment.WHSCODE).type == "GM"
