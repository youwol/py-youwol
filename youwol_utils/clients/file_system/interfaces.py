import io
from abc import ABC, abstractmethod
from typing import Dict


class FileSystemInterface(ABC):

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
