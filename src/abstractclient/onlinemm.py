import logging
from dataclasses import dataclass, is_dataclass, field
from datetime import time, datetime
from typing import Dict, Optional
from requests import HTTPError, Timeout

from .http import HTTPFactory


def nested_dataclass(*args, **kwargs):
    def wrapper(cls):
        cls = dataclass(cls, **kwargs)
        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            for name, value in kwargs.items():
                field_type = cls.__annotations__.get(name, None)
                if is_dataclass(field_type) and isinstance(value, dict):
                    new_obj = field_type(**value)
                    kwargs[name] = new_obj
            original_init(self, *args, **kwargs)

        cls.__init__ = __init__
        return cls

    return wrapper(args[0]) if args else wrapper


@nested_dataclass
class UnitInfo:

    @nested_dataclass
    class WorkTime:
        open: time = field(default_factory=datetime.now)
        close: time = field(default_factory=datetime.now)

        def __post_init__(self):
            try:
                self.open = datetime.strptime(self.open, '%H:%M:%S').time()
                self.close = datetime.strptime(self.close, '%H:%M:%S').time()
            except (ValueError, TypeError):
                pass

    name: str = None
    status: str = None
    type: str = None
    work_time: WorkTime = field(default_factory=WorkTime)

    def __post_init__(self):
        self.type = self.translate()

    def translate(self) -> Optional[str]:
        if not self.type:
            return None
        cyrillic = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
        latin = 'a|b|v|g|d|e|e|zh|z|i|i|k|l|m|n|o|p|r|s|t|u|f|kh|c|ch|sh|shch||y||e|iu|ia'.split('|')
        tr = {k: v for k, v in zip(cyrillic, latin)}
        return "".join([tr.get(ch.lower(), ch).upper() for ch in self.type])


def get_info(config: Dict, whscode: str) -> UnitInfo:
    """
    Запрашивает информацию из сервиса onlinemm

    Args:
        config: Словарь, с настройками класса  HTTPFactory для доступа к сервису onlinemm
        whscode: Код объекта

    Returns:
        Информация об ОО

    """
    logging.info(f"Запрос формата ОО в сервисе 'onlinemm'. Параметры подключения: {config}")

    try:
        http = HTTPFactory(config)
        response: Dict = http.execute(
            method="info",
            dynamic_values={
                "whscode": whscode,
            }
        ) or dict()

        return UnitInfo(**response.get("result", {}))

    except (HTTPError, ConnectionError, Timeout, TypeError, ValueError) as e:
        logging.error(f"Ошибка при получении данных: {str(e)}")
        return UnitInfo()
