# standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.context import Context


@dataclass
class DownloadTask(ABC):
    """
    Abstract definition of a download task for asset.
    """

    process_id: str
    """
    Process ID (uid).
    """
    raw_id: str
    """
    Asset's raw ID.
    """
    asset_id: str
    """
    Asset's ID.
    """
    url: str
    """
    URL that triggered the download.
    """

    @abstractmethod
    async def is_local_up_to_date(self, context: Context):
        pass

    @abstractmethod
    async def create_local_asset(self, context: Context):
        pass

    @abstractmethod
    def download_id(self):
        pass
