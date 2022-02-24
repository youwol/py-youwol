import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Union

from starlette.requests import Request

from youwol_utils import (
    to_group_id, flatten, generate_headers_downstream,
    ReadPolicyEnumFactory, SharePolicyEnumFactory, base64, log_info,
)
from .configurations import Configuration
from .models import ItemResponse, AssetResponse, GroupAccess, FolderResponse, AssetWithPermissionResponse, \
    PermissionsResponse
from .raw_stores.interface import AssetMeta


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = await config.admin_headers if config.admin_headers else {}
    log_info("Successfully retrieved authorization for resources creation")
    doc_db = config.data_client.docdb
    storage = config.data_client.storage
    await asyncio.gather(
        doc_db.ensure_table(headers=headers),
        storage.ensure_bucket(headers=headers)
    )
    log_info("resources initialization done")


def chrono(t0):
    now = time.time()
    return 1000 * int(100 * (now - t0)) / 100, now


async def get_items(
        folder_id: str,
        headers: Dict[str, str],
        configuration: Configuration
):
    resp = await configuration.treedb_client.get_children(folder_id, headers=headers)
    return resp['items']


async def get_items_rec(
        folder_id: str,
        headers: Dict[str, str],
        configuration: Configuration
) -> List[any]:
    treedb_client = configuration.treedb_client
    resp = await treedb_client.get_children(folder_id, headers=headers)

    items_children = await asyncio.gather(*[
        get_items_rec(folder_id=folder['folderId'], headers=headers, configuration=configuration)
        for folder in resp["folders"]
    ])

    return list(flatten([resp["items"]] + list(items_children)))


def to_item_resp(item) -> ItemResponse:
    meta = json.loads(item['metadata'])
    return ItemResponse(name=item['name'], treeId=item['itemId'], folderId=item['folderId'], kind=item["type"],
                        groupId=item['groupId'], driveId=item['driveId'], assetId=item["relatedId"],
                        rawId=meta['relatedId'], borrowed=meta["borrowed"])


def to_folder_resp(folder) -> FolderResponse:
    return FolderResponse(name=folder["name"], folderId=folder['folderId'], parentFolderId=folder["parentFolderId"],
                          driveId=folder["driveId"])


def to_asset_resp(asset, permissions: PermissionsResponse = None) -> Union[AssetResponse, AssetWithPermissionResponse]:
    group_id = asset['groupId'] if 'groupId' in asset else to_group_id(asset['scope'])
    if permissions:
        return AssetWithPermissionResponse(
            **{**asset, **{"rawId": asset["relatedId"], "groupId": group_id, "permissions": permissions}})
    return AssetResponse(**{**asset, **{"rawId": asset["relatedId"], "groupId": group_id}})


async def extract_request_data(request: Request):
    form = await request.form()
    file = form.get('file')
    body = None
    if not file:
        body = await request.body()
        body = json.loads((await request.body()).decode('utf8')) if body else None

    return body, file, request.query_params


def to_asset_meta(body: Dict[str, Any]):
    group_id = body['groupId'] if 'groupId' in body else to_group_id(body['scope'])

    return AssetMeta(name=body['name'], description=body['description'], kind=body['kind'], groupId=group_id,
                     tags=body['tags'])


async def regroup_asset(
        request: Request,
        asset: AssetResponse,
        tree_item: Dict[str, str],
        configuration: Configuration
):
    headers = generate_headers_downstream(request.headers)
    new_group_id = tree_item['groupId']
    tree_db, assets_db, assets_stores = configuration.treedb_client, configuration.assets_client, \
                                        configuration.assets_stores()

    # from here we change the owner of the group, extra care is needed
    store = next(store for store in assets_stores if store.path_name == asset.kind)
    body_asset = {**asset.dict(), **{"groupId": new_group_id}}
    body_raw = AssetMeta(**body_asset)
    await asyncio.gather(
        assets_db.update_asset(asset_id=asset.assetId, body=body_asset, headers=headers),
        store.sync_asset_metadata(request=request, raw_id=asset.rawId, metadata=body_raw, headers=headers)
    )

    new_asset = ItemResponse(**{**asset.dict(),
                                **{"groupId": new_group_id,
                                   "treeId": tree_item['itemId'],
                                   "borrowed": False,
                                   "folderId": tree_item['folderId'],
                                   "driveId": tree_item['driveId']}
                                })
    return new_asset


def format_policy(policy: Any) -> GroupAccess:
    if policy["read"] not in ReadPolicyEnumFactory:
        raise Exception("Read policy not known")

    if policy["share"] not in SharePolicyEnumFactory:
        raise Exception("Share policy not known")

    expiration = None
    if policy['read'] == "expiration-date":
        deadline = policy['timestamp'] + policy['parameters']['period']
        expiration = str(datetime.fromtimestamp(deadline))

    return GroupAccess(read=ReadPolicyEnumFactory[policy["read"]],
                       expiration=expiration,
                       share=SharePolicyEnumFactory[policy["share"]])


def raw_id_to_asset_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


def asset_id_to_raw_id(asset_id) -> str:
    b = str.encode(asset_id)
    return base64.urlsafe_b64decode(b).decode()
