# standard library
from pathlib import Path

# typing
from typing import NamedTuple


class FileData(NamedTuple):
    objectName: str | Path
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str
    owner: str | None
