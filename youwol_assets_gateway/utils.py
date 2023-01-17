from datetime import datetime
from typing import Dict, Any, List, Union, Optional

from pydantic import BaseModel

from youwol_utils import to_group_id, base64
from youwol_utils.http_clients.assets_backend import ReadPolicyEnumFactory, SharePolicyEnumFactory
from youwol_utils.http_clients.assets_gateway import AssetResponse, GroupAccess, \
    AssetWithPermissionResponse, PermissionsResponse


def to_asset_resp(asset, permissions: PermissionsResponse = None) -> Union[AssetResponse, AssetWithPermissionResponse]:
    group_id = asset['groupId'] if 'groupId' in asset else to_group_id(asset['scope'])
    if permissions:
        return AssetWithPermissionResponse(
            **{**asset, **{"groupId": group_id, "permissions": permissions}})
    return AssetResponse(**{**asset, **{"groupId": group_id}})


def format_policy(policy: Any) -> GroupAccess:
    if policy["read"] not in ReadPolicyEnumFactory:
        raise RuntimeError("Read policy not known")

    if policy["share"] not in SharePolicyEnumFactory:
        raise RuntimeError("Share policy not known")

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
    dynamic_fields: Optional[Dict[str, Union[str, float, int]]] = None
