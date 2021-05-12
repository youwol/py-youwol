import json
from typing import Union

from dataclasses import dataclass
from fastapi import HTTPException
from starlette.requests import Request

from youwol_utils import (to_group_scope, RecordsResponse)
from .interface import (RawStore, RawId, AssetMeta)

"""
@dataclass(frozen=True)
class UpdateDependencies(Action):

    name: str = "update-dependencies"

    async def execute(self, request: Request, client: FluxClient, raw_id: str,  rest_of_path: Union[str, None],
                      headers):

        body = json.loads((await request.body()).decode('utf8'))
        return await client.update_metadata(project_id=raw_id, body=body)
"""


@dataclass(frozen=True)
class FluxProjectsStore(RawStore):

    path_name = 'flux-project'

    async def create_asset(self, request: Request, metadata: AssetMeta, headers) -> (RawId, AssetMeta):

        body = await request.body()
        body = json.loads((await request.body()).decode('utf8')) if body else None

        if body is None:
            body = {
                "name": metadata.name,
                "description": metadata.description,
                "scope": to_group_scope(metadata.groupId),
                "fluxPacks": []
                }
            resp = await self.client.create_project(body=body, headers=headers)
            return resp['projectId'], AssetMeta()

        resp = await self.client.create_project(body=body, headers=headers)
        return resp['projectId'], AssetMeta()

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):

        actual_meta = await self.client.get_metadata(project_id=raw_id, headers=headers)
        body = {**actual_meta,
                **{k: v for k, v in metadata.dict().items() if k in ['name', 'description'] and v},
                **{"scope": to_group_scope(metadata.groupId) if metadata.groupId else actual_meta['scope']}
                }

        return await self.client.update_metadata(project_id=raw_id, body=body, headers=headers)

    async def update_asset(self, request: Request, raw_id: str,  metadata: AssetMeta, rest_of_path: str, headers):

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
                "fluxComponents": body['fluxComponents'],
                "fluxPacks": body['fluxPacks'],
                "libraries": body['libraries'] if "libraries" in body else None,
                "scope": "/youwol-users"
                }
            return await self.client.update_metadata(project_id=raw_id, body=body_new, headers=headers)
        raise HTTPException(status_code=404, detail='Endpoint not found')

    async def get_asset(self, request: Request, raw_id: str,  rest_of_path: Union[str, None], headers):
        return await self.client.get_project(project_id=raw_id, headers=headers)

    async def delete_asset(self, request: Request, raw_id, headers):
        return await self.client.delete_project(raw_id, headers=headers)

    async def get_records(self, request: Request, raw_ids: str, group_id: str, headers):

        body = {"ids": raw_ids, "groupId": group_id}
        resp = await self.client.get_records(body=body, headers=headers)
        return RecordsResponse(**resp)
