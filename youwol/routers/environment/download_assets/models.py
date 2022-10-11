from abc import ABC, abstractmethod
from dataclasses import dataclass

from youwol_utils.context import Context


@dataclass
class DownloadTask(ABC):
    process_id: str
    raw_id: str
    asset_id: str
    url: str

    @abstractmethod
    async def is_local_up_to_date(self, context: Context):
        pass

    @abstractmethod
    async def create_local_asset(self, context: Context):
        pass

    @abstractmethod
    async def download_id(self):
        pass
