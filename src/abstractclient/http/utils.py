from typing import Any, Dict, Optional, IO, Union
from requests import Request, Session

MAX_BODY_LENGTH: int = 500


def curlify(url: str, method: str, session: Session = None, data: Optional[Any] = None,
            data_json: Optional[Dict] = None, file: Optional[Union[Dict, IO]] = None, **kwargs) -> str:
    """
    Формируте текстовое представление CURL запроса к ресурсу

    Args:
        url: URL адрес ресурса
        method: Метод запроса (POST, GET)
        session: Настроенная сессия
        data: Данные
        data_json: JSON Данные
        file: Данные в виде файлов
        **kwargs: Прочие параметры запроса

    Returns:
        Строковое представление CURL запроса

    """
    r = Request(method, url, session.headers, auth=session.auth, files=file, data=data, json=data_json,
                params=kwargs).prepare()
    headers_string: str = " -H ".join(['"{0}: {1}"'.format(k, v) for k, v in r.headers.items()])
    body_string: str = repr(r.body)[2:-1]

    if len(body_string) > MAX_BODY_LENGTH:
        body_string = "Long body string replaced here !"

    return f"curl -X {r.method} -H {headers_string} -d '{body_string}' {r.url}"
