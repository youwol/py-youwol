from abc import ABC
from dataclasses import dataclass
from typing import Union

import aiohttp
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import (raise_exception_from_response)
from .interface import (AssetMeta, RawStore, RawId)


@dataclass(frozen=True)
class PackagesStore(RawStore, ABC):
    path_name = 'package'

    async def create_asset(self, request: Request, metadata: AssetMeta, rest_of_path: str, headers) \
            -> (RawId, AssetMeta):

        form = await request.form()
        form = {
            'file': await form.get('file').read(),
            'content_encoding': form.get('content_encoding', 'identity')
        }
        async with aiohttp.ClientSession() as session:
            async with await session.post(self.client.publish_url, data=form, headers=headers) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    return resp_json['id'], AssetMeta(name=resp_json['name'])
                await raise_exception_from_response(resp, url=self.client.publish_url, headers=headers)

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):
        pass

    async def get_asset(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):

        url = "/".join([self.client.url_base, "resources", raw_id, rest_of_path])
        async with aiohttp.ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    return Response(content=content, headers={h: resp.headers.get(h) for h in resp.headers.keys()})
                await raise_exception_from_response(resp, url=url, headers=headers)

    async def get_asset_metadata(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        return await self.client.get_versions(raw_id, headers=headers)

    async def delete_asset(self, request: Request, raw_id, headers):
        pass
