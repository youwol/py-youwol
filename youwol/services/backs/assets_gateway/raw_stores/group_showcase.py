import json
from abc import ABC

from dataclasses import dataclass
from starlette.requests import Request

from youwol_utils import RecordsResponse, RecordsDocDb, RecordsStorage
from .interface import (AssetMeta, RawStore, RawId)


@dataclass(frozen=True)
class GroupShowCaseStore(RawStore, ABC):
    path_name = 'group-showcase'

    async def create_asset(self, request: Request, metadata: AssetMeta, headers) -> (RawId, AssetMeta):
        body = await request.body()
        body = json.loads((await request.body()).decode('utf8')) if body else None
        showcase_id = body['showcaseGroupId']
        name = body['name']
        return showcase_id, AssetMeta(name=name, dynamic_fields={"showcaseGroupId": showcase_id})

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):
        pass

    async def delete_asset(self, request: Request, raw_id, headers):
        pass

    async def get_records(self, request: Request, raw_ids: str, group_id: str, headers):
        # For now there is no records associated to a 'group-showcase' entity
        return RecordsResponse(docdb=RecordsDocDb(keyspaces=[]), storage=RecordsStorage(buckets=[]))


"""

@router.post("/groups", response_model=AssetResponse, summary="expose a group")
async def expose_group(request: Request, expose_body: ExposeGroupBody):

    headers = generate_headers_downstream(request.headers)
    tree_db = configuration.treedb_client
    asset_db = configuration.assets_client
    body_tree = {
        "name": expose_body.name,
        "type": "exposed-group",
        "metadata": json.dumps({
            "exposedGroupId": expose_body.groupId,
            "assetId": expose_body.groupId,
            "relatedId": expose_body.groupId,
            "borrowed": False
            })
        }
    body_asset = {
        "relatedId": expose_body.groupId,
        "kind": "exposed-group"
        }

    resp0, resp1 = await asyncio.gather(
        tree_db.create_item(folder_id=expose_body.folderId, body=body_tree, headers=headers),
        asset_db.create_asset(body=body_asset, headers=headers)
        )

    scope = to_group_scope(resp0['groupId'])

    body_asset = {"name": expose_body.name, "tags": [], "description": "", "scope": scope}
    await asset_db.update_asset(asset_id=resp1['assetId'], body=body_asset, headers=headers)
    return AssetResponse(assetId=resp1['assetId'], description="", images=[], thumbnails=[], kind="exposed-group",
                         treeId=resp0['itemId'], name=expose_body.name, relatedId=expose_body.groupId,
                         groupId=resp0['groupId'], tags=[])

"""
