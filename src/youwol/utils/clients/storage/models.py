# standard library
from pathlib import Path

# typing
from typing import NamedTuple, Union


class FileData(NamedTuple):
    objectName: Union[str, Path]
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str
    owner: Union[str, None]
