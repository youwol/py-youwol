from abc import ABC
from dataclasses import dataclass

from youwol_utils.context import Context


@dataclass
class DownloadTask(ABC):
    process_id: str
    raw_id: str
    asset_id: str
    url: str
    context: Context
