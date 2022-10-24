import json
from http import HTTPStatus
from requests import Response
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from json import JSONDecodeError
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError, Element
from typing import Optional, Dict, Union, List, Tuple, IO

from ..abstractpipeline import ExtractStrategy

# Пользовательская типизация
DeserializedHTTPResponse = Union[bytes, str, dict, List[dict], Element, None]
DeserializedHTTPRequestBody = Optional[Union[Dict, List[Tuple], bytes, IO]]


class NullExtractStrategy(ExtractStrategy):
    """
    Извлекает данные без преобразования
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Dict[str, dict]:
        response.encoding = code
        content: DeserializedHTTPResponse = response.text

        return content


class JSONExtractStrategy(ExtractStrategy):
    """
    Стратегия извлечения JSON
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Optional[dict]:
        response.encoding = code
        content: DeserializedHTTPResponse = {}

        # Если статус 204 - возвращаем дефолтное значение
        if response.status_code == HTTPStatus.NO_CONTENT:
            return content

        try:
            content: DeserializedHTTPResponse = response.json()
        except (JSONDecodeError, TypeError):
            self.logger.warning("Ответ сервера содержит не валидный JSON")

        return content


class XMLExtractStrategy(ExtractStrategy):
    """
    Стратегия извлечения XML
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Optional[Element]:
        content: DeserializedHTTPResponse = None

        # Если статус 204 - возвращаем дефолтное значение
        if response.status_code == HTTPStatus.NO_CONTENT:
            return content

        try:
            content: Element = ElementTree.fromstring(response.content)
        except ParseError:
            self.logger.warning("Ответ сервера содержит не валидный XML")

        return content


class ZIPXMLExtractStrategy(ExtractStrategy):
    """
    Стратегия извлечения ZIP архива с XML
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Dict[str, Element]:
        content: DeserializedHTTPResponse = {}

        # Если статус 204 - возвращаем дефолтное значение
        if response.status_code == HTTPStatus.NO_CONTENT:
            return content

        try:
            zf: ZipFile = ZipFile(BytesIO(response.content))
        except BadZipFile:
            self.logger.warning(f"Получен некорректный zip файл. Не удалось распаковать")
            return content

        for file in zf.filelist:
            file_content: bytes = zf.read(file)
            try:
                xml: Element = ElementTree.fromstring(file_content)
                content[file.filename] = xml
            except ParseError:
                self.logger.warning(f"Файл архива {file.filename} содержит не валидный XML")
                content[file.filename] = file_content

        return content


class ZIPJSONExtractStrategy(ExtractStrategy):
    """
    Стратегия извлечения ZIP архива с JSON
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Dict[str, dict]:
        content: DeserializedHTTPResponse = {}

        # Если статус 204 - возвращаем дефолтное значение
        if response.status_code == HTTPStatus.NO_CONTENT:
            return content

        try:
            zf: ZipFile = ZipFile(BytesIO(response.content))
        except BadZipFile:
            self.logger.warning(f"Получен некорректный zip файл. Не удалось распаковать")
            return content

        for file in zf.filelist:
            file_content: bytes = zf.read(file)
            if code:
                file_content: str = file_content.decode(code)
            try:
                content[file.filename] = json.loads(file_content)
            except (JSONDecodeError, TypeError):
                self.logger.warning(f"Файл архива {file.filename} содержит не валидный JSON")
                content[file.filename] = file_content

        return content


class ZIPExtractStrategy(ExtractStrategy):
    """
    Стратегия извлечения ZIP архива c произвольным содержанием
    """

    def extract(self, response: Response, code: Optional[str] = None) -> Dict[str, dict]:
        content: DeserializedHTTPResponse = {}

        # Если статус 204 - возвращаем дефолтное значение
        if response.status_code == HTTPStatus.NO_CONTENT:
            return content

        try:
            zf: ZipFile = ZipFile(BytesIO(response.content))
        except BadZipFile:
            self.logger.warning(f"Получен некорректный zip файл. Не удалось распаковать")
            return content

        for file in zf.filelist:
            file_content: bytes = zf.read(file)
            content[file.filename] = file_content.decode(code) if code else file_content

        return content
