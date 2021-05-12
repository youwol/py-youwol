
from abc import ABC
from datetime import datetime
from dataclasses import dataclass
from starlette.requests import Request

from youwol_utils.clients.data_api.data import DataClient
from ..raw_stores.data import DataStore
from .interface import (RawId, AssetMeta)


@dataclass(frozen=True)
class DrivePackStore(DataStore, ABC):
    client: DataClient
    path_name = 'drive-pack'

    async def create_asset(self, request: Request, metadata: AssetMeta, headers) -> (RawId, AssetMeta):

        raw_id, meta = await super().create_asset(request, metadata, headers)
        meta_new = AssetMeta(
            name=meta.name,
            description="Drive package at "+datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            kind=meta.kind,
            images=meta.images,
            groupId=meta.groupId,
            tags=meta.tags,
            dynamic_fields=meta.tags)

        return raw_id, meta_new
