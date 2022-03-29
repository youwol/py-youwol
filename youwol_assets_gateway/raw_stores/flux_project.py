import json
from dataclasses import dataclass
from typing import Union

from fastapi import HTTPException
from starlette.requests import Request

from youwol_utils import (to_group_scope)
from .interface import (RawStore, RawId, AssetMeta)


@dataclass(frozen=True)
class FluxProjectsStore(RawStore):
    path_name = 'flux-project'

    async def create_asset(self, request: Request, metadata: AssetMeta, rest_of_path: str, headers) \
            -> (RawId, AssetMeta):

        body = await request.body()
        body = json.loads((await request.body()).decode('utf8')) if body else None

        if body is None:
            body = {
                "name": metadata.name,
                "description": metadata.description,
                "scope": to_group_scope(metadata.groupId),
                "fluxPacks": []
            }

        if 'projectId' in body:
            await self.client.update_project(project_id=body['projectId'], body=body, headers=headers)
            return body['projectId'], AssetMeta(name=body["name"])

        resp = await self.client.create_project(body=body, headers=headers)
        return resp['projectId'], AssetMeta(name=body["name"], description=body["description"])

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):

        actual_meta = await self.client.get_metadata(project_id=raw_id, headers=headers)
        body = {**actual_meta,
                **{k: v for k, v in metadata.dict().items() if k in ['name', 'description'] and v},
                **{"scope": to_group_scope(metadata.groupId) if metadata.groupId else actual_meta['scope']}
                }

        return await self.client.update_metadata(project_id=raw_id, body=body, headers=headers)

    async def get_asset_metadata(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        await self.client.get_metadata(project_id=raw_id, headers=headers)

    async def update_asset(self, request: Request, raw_id: str, metadata: AssetMeta, rest_of_path: str, headers):

        if rest_of_path == "":
            body = json.loads((await request.body()).decode('utf8'))
            body = {**body, **{"name": metadata.name,
                               "description": metadata.description,
                               "scope": "/youwol-users"
                               }
                    }
            return await self.client.update_project(project_id=raw_id, body=body, headers=headers)

        if rest_of_path == "metadata":
            body = json.loads((await request.body()).decode('utf8'))
            actual_meta = await self.client.get_metadata(project_id=raw_id, headers=headers)
            body_new = {
                "name": metadata.name if metadata.name else actual_meta["name"],
                "description": metadata.description if metadata.description else actual_meta["description"],
                "libraries": body['libraries'] if "libraries" in body else {}
            }
            return await self.client.update_metadata(project_id=raw_id, body=body_new, headers=headers)
        raise HTTPException(status_code=404, detail='Endpoint not found')

    async def get_asset(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):
        return await self.client.get_project(project_id=raw_id, headers=headers)

    async def delete_asset(self, request: Request, raw_id, headers):
        return await self.client.delete_project(raw_id, headers=headers)
