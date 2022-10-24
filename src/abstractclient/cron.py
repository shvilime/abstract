import re
import random
import logging
from crontab import CronTab
from dataclasses import dataclass, field
from typing import List, Optional, Pattern, Dict


@dataclass
class CronTask:
    active: bool
    branch_type: List[str]
    time: List[str]
    command: str
    comment: str
    variables: Optional[Dict] = field(default_factory=dict)

    def __post_init__(self):
        self.replace_rnd(self.time)
        self.replace_var(self.time, self.variables)

    @staticmethod
    def replace_rnd(lst: List[str]):
        pattern: Pattern = re.compile(r"[rR][nN][dD]\s*\(\s*([0-9]|[0-5][0-9])\s*,\s*([0-9]|[0-5][0-9])\s*\)")
        for num, el in enumerate(lst):
            for match in re.finditer(pattern, el):
                lst[num] = re.sub(pattern, str(random.randint(int(match[1]), int(match[2]))), lst[num], 1)

    @staticmethod
    def replace_var(lst: List[str], variables: Dict):
        pattern: Pattern = re.compile(r"[vV][aA][rR]\s*\(\s*(\w*)\s*\)")
        for num, el in enumerate(lst):
            for match in re.finditer(pattern, el):
                variable = variables.get(match[1])
                if variable is None:
                    raise TypeError(f"В словаре variables отсутствет переменная {match[1]}")
                lst[num] = re.sub(pattern, str(variable), lst[num], 1)


def setup_cron(application: str, user: str, mode: str, tasks: List[CronTask]) -> bool:
    """
    Загрузка заданий CronTab из конфигурационных файлов

    Args:
        application: Наименование приложения
        user: Имя пользователя, для которого настраиваются задания CronTab
        mode: Режим запуска клиента (тип ОО) для проверки соответствия задач
        tasks: Список с задачами

    """
    # Создадим объект CronTab, для заданного пользователя
    crontab: CronTab = CronTab(user=user)

    # Чистим CronTab от существующих задач, для приложения application
    for job in crontab.crons[:]:
        # Если задание не для текущего клиента - пропустим
        if application.upper() not in job.comment.upper():
            continue

        crontab.remove(job)
        logging.debug(f"У пользователя '{user}' удалена задача: {job}")

    # Создадим новые задания
    for task in tasks:
        # Если у задачи отсутствует комментарий - поругаемся и пропустим
        if not task.comment:
            logging.error(f"Отсутствует комментарий в задании: {task}")
            continue
        # Если тип ОО не подходит для данной задачи, то пропустим
        if mode not in task.branch_type:
            logging.debug(f"Пропущен не подходящий тип задания для данного типа ОО: {task}")
            continue

        job = crontab.new(command=task.command, comment=f"{application}: {task.comment}")

        # Настроим задачу: активность, интервалы запуска
        try:
            job.enable(task.active)
            job.setall(*task.time)
            logging.debug(f"Пользователю '{user}' установлено cron задание '{job}'")
        except (ValueError, KeyError) as e:
            logging.error(f"Не правильно задан параметр ({str(e)}) для задания cron '{task}'")
            return False

    # Сохраним CronTab со всеми изменениями в заданиях
    try:
        crontab.write_to_user(user)
    except (OSError, IOError) as e:
        logging.error(f"Ошибка при записи CronTab\n{str(e)}")
        return False

    return True
