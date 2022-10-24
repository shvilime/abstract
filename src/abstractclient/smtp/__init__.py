# -*- coding: utf-8 -*-
import os
import logging
from typing import Dict, List, Optional, Tuple, Union, IO
from smtplib import SMTP, SMTPException
from email.message import EmailMessage

from ..abstractpipeline import AbstractFactory

# Пользовательская типизация
Filename = Union[str, bytes, os.PathLike]
MimeType = str


class SMTPFactory(AbstractFactory):
    """
    Фабрика коннектов SMTP
    """

    __sessions: Dict[str, Dict] = dict()

    def __init__(self, config: Dict):
        """
        Настройка подключения

        Args:
            config: Словарь с настройками подключения

        """
        self.logger = logging.getLogger(__name__)
        self.__config = config
        self.setup_sessions()

    def setup_sessions(self, cfg: Optional[List[Dict]] = None):
        """
        Настройка подключения через SMTP

        cfg: Список словарей с настройками

        Returns:
            Sessions: Словарь с настроенными сессиями

        """

        # Получим список настрок сессии из переданных параметров или считаем из системных настроек
        config: Dict = cfg if cfg else self.__config.get('sessions', None)

        if not config:
            raise ValueError("Не заданы настройки сессий. Проверьте в конфигурации раздел transport.sessions")

        for item in config:
            host: str = item.get("host")
            port: int = item.get("port", 0)

            if not host:
                raise ValueError("Не задан адрес хоста")

            self.__sessions[item.get("alias").lower()] = dict(
                connect=dict(host=host, port=port),
                credentials=dict(user=item.get("username"),
                                 password=item.get("password")),
                login=True if item.get("username") or item.get("password") else False,
                tls=item.get("tls", False)
            )

    def send(self, from_mail: str, mailto: Union[str, List[str]], subject: Optional[str] = "",
             message: Optional[str] = "", files: List[Tuple[Filename, MimeType, Union[str, IO]]] = None):
        """
        Отправляет письма по SMTP протоколу

        Args:
            from_mail: Адрес отправителя
            mailto: Адрес или список адресов получаетелей
            subject: Тема письма
            message: Текст сообщения
            files: Список отправляемых файлов

        """
        if not files:
            files = []
        if isinstance(mailto, str):
            mailto = [mailto]

        # Подготовка сообщения к отправке
        msg = EmailMessage()
        msg["From"] = from_mail
        msg["To"] = ",".join(mailto)
        msg["Subject"] = subject
        msg.set_content(message)

        # Добавим к сообщению приложения
        for filename, mimetype, file in files:
            if hasattr(file, "read"):
                data = file.read()
            elif os.path.exists(file):
                with open(file, "rb") as f:
                    data = f.read()

            maintype, subtype = mimetype.split("/", 1)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)

        # Отправка сообщения будет последовательно выполняться для всех сессий, заданных в конфигурации, до успеха
        for i, (key, session) in enumerate(self.__sessions.items()):
            try:
                self.logger.debug(f"Попытка отправки письма в рамках сессии: {key}")
                self.logger.debug(f"От: {from_mail} в адрес {mailto}, заголовок {subject}\n"
                                  f"Текст {message}\nПриложения: {files}")

                smtp: SMTP = SMTP(**session.get("connect"))
                if session.get("tls", False):
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                if session.get("login", False):
                    smtp.login(**session.get("credentials"))
                smtp.send_message(msg)
                smtp.quit()

                break

            except (SMTPException, TimeoutError) as e:
                self.logger.exception(f"Ошибка при отправке письма: {str(e)}")
                if i == len(self.__sessions) - 1:
                    raise
