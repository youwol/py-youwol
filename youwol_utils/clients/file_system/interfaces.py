import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class FileObject:
    """
    Subset of Minio's Object class used in youwol
    """
    bucket_name: str
    object_name: str


class FileSystemInterface(ABC):

    @abstractmethod
    async def ensure_bucket(self):
        raise NotImplementedError

    @abstractmethod
    async def put_object(self, object_name: str, data: io.BytesIO, metadata: Dict[str, str] = None, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_info(self, object_name: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def set_metadata(self, object_name: str, metadata: Dict[str, str], **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_object(self, object_name: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def remove_object(self, object_name: str, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def remove_folder(self, prefix: str, raise_not_found: bool, **kwargs):
        pass

    @abstractmethod
    async def list_objects(self, prefix: str, recursive: bool, **kwargs) -> Iterable[FileObject]:
        pass
