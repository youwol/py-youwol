from dataclasses import dataclass
from typing import Union, Dict, List, Any

from pydantic import BaseModel
from starlette.requests import Request

RawId = str


class AssetImg(BaseModel):
    name: str
    content: bytes


class AssetMeta(BaseModel):
    name: Union[str, None] = None
    description: Union[str, None] = None
    images: Union[List[AssetImg], None] = None  # name, bytes
    kind: Union[str, None] = None
    groupId: Union[str, None] = None
    tags: Union[List[str], None] = None
    dynamic_fields: Dict[str, Union[str, float, int]] = None


@dataclass(frozen=True)
class RawStore:
    client: Any

    async def create_asset(self, request: Request, metadata: AssetMeta, rest_of_path: str, headers) \
            -> (RawId, AssetMeta):
        raise NotImplementedError

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):
        raise NotImplementedError

    async def update_asset(self, request: Request, raw_id: str, metadata: AssetMeta, rest_of_path: Union[str, None],
                           headers):
        raise NotImplementedError

    async def get_asset(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        raise NotImplementedError

    async def get_asset_metadata(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        raise NotImplementedError

    async def delete_asset(self, request: Request, raw_id, headers):
        raise NotImplementedError
