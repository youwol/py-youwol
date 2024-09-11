# standard library
import datetime

from collections.abc import Callable, Iterable
from enum import Enum
from pathlib import Path, PosixPath

# typing
from typing import Any, Union

# third parties
from pydantic import BaseModel

# 'Any' should be 'JSON', but pydantic scream (most likely because of recursive definition)
# pylint: disable-next=invalid-name"
JSON = Union[str, int, float, bool, None, dict[str, Any], list]
"""
Basically means a valid JSON object.

The type definition is not rigorous (recursive definition cause problem with pydantic).
"""

AnyDict = dict[str, Any]
"""
A loosely type dictionary indexed by strings.
Often used to refers to a JSON object with no schema validation.
"""


def to_serializable_json_leaf(v):
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, PosixPath):
        return str(v)
    if isinstance(v, Callable):
        return {}
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, Iterable) and not isinstance(v, list) and not isinstance(v, str):
        v = list(v)
    if isinstance(v, datetime.datetime):
        return str(v)
    if isinstance(v, (int, float, str, bool)):
        return v
    if v is None:
        return None
    # This is the case of a custom class not deriving from 'BaseModel' => no serialization
    return {}


def is_json_leaf(v):
    return (
        not isinstance(v, dict)
        and not isinstance(v, list)
        and not isinstance(v, BaseModel)
    )


def to_json_rec(_obj: AnyDict | list[Any] | JSON):
    def process_value(value):
        if is_json_leaf(value):
            return to_serializable_json_leaf(value)
        if isinstance(k, BaseModel):
            return to_json_rec(value.dict())
        return to_json_rec(value)

    if isinstance(_obj, dict):
        r_dict = {}
        for k, v in _obj.items():
            r_dict[k] = process_value(v)
        return r_dict

    if isinstance(_obj, list):
        r_list = []
        for k in _obj:
            r_list.append(process_value(k))
        return r_list

    return {}


def to_json(obj: BaseModel | JSON) -> JSON:
    base = obj.dict() if isinstance(obj, BaseModel) else obj
    return to_json_rec(base)
