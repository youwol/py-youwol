from abc import ABC, abstractmethod
from dataclasses import dataclass

from youwol_utils.context import Context


@dataclass
class UploadTask(ABC):
    raw_id: str
    asset_id: str
    context: Context

    @abstractmethod
    async def get_raw(self) -> bytes:
        pass

    @abstractmethod
    async def create_raw(self, data: bytes, folder_id: str):
        pass

    @abstractmethod
    async def update_raw(self, data: bytes, folder_id: str):
        pass
