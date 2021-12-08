import asyncio
import json
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict
from configuration import Context, RemoteClients, YouwolConfiguration
from aiohttp import FormData

from utils_paths import parse_json, write_json
from youwol_utils import JSON
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient


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

