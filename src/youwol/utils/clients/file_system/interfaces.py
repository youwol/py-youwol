# standard library
import io

from abc import ABC, abstractmethod
from dataclasses import dataclass

# typing
from typing import Iterable, List, Optional, Tuple

# third parties
from pydantic import BaseModel


@dataclass(frozen=True)
class FileObject:
    """
    Subset of Minio's Object class used in youwol
    """

    bucket_name: str
    object_id: str


class Metadata(BaseModel):
    fileName: Optional[str]
    contentType: Optional[str]
    contentEncoding: Optional[str]


class FileSystemInterface(ABC):
    @abstractmethod
    async def ensure_bucket(self):
        raise NotImplementedError

    @abstractmethod
    async def put_object(
        self,
        object_id: str,
        data: io.BytesIO,
        object_name: str,
        content_type: str,
        content_encoding: str,
        **kwargs,
    ):
        raise NotImplementedError

    @abstractmethod
    async def get_info(self, object_id: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def set_metadata(self, object_id: str, metadata: Metadata, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_object(
        self, object_id: str, ranges_bytes: List[Tuple[int, int]] = None, **kwargs
    ):
        raise NotImplementedError

    @abstractmethod
    async def remove_object(self, object_id: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def remove_folder(self, prefix: str, raise_not_found: bool, **kwargs):
        pass

    @abstractmethod
    async def list_objects(
        self, prefix: str, recursive: bool, **kwargs
    ) -> Iterable[FileObject]:
        pass
