from getpass import getuser
from src.abstractclient import environment
from src.abstractclient.cron import CronTask, setup_cron


def test_cron():
    """
    Тест проверки заданий крон
    """
    tasks = []
    for item in environment.CRON.get("tasks", []):
        try:
            tasks.append(CronTask(**item, variables=environment.CRON.variables))
        except TypeError:
            assert False

    result_set: bool = setup_cron(environment.APPLICATION, getuser(), environment.MODE, tasks)
    result_del: bool = setup_cron(environment.APPLICATION, getuser(), environment.MODE, [])

    assert result_set and result_del
