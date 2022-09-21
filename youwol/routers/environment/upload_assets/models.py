from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any

from youwol_utils.context import Context


@dataclass
class UploadTask(ABC):
    remote_host: str
    raw_id: str
    asset_id: str
    options: Optional[Any] = None

    @abstractmethod
    async def get_raw(self, context: Context) -> bytes:
        pass

    @abstractmethod
    async def create_raw(self, data: bytes, folder_id: str, context: Context):
        pass

    @abstractmethod
    async def update_raw(self, data: bytes, folder_id: str, context: Context):
        pass
