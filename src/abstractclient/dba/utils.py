# -*- coding: utf-8 -*-
import json
from decimal import Decimal
from typing import Any


class GenericJSONEncoder(json.JSONEncoder):
    """
    Сериализатор
    """

    def default(self, obj: Any):
        if isinstance(obj, str):
            return obj
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return obj.decode("utf8")
        else:
            return obj.to_dict() if hasattr(obj, 'to_dict') else str(obj)
