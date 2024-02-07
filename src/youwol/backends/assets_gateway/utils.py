# standard library
from datetime import datetime

# typing
from typing import Any

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import base64, to_group_id
from youwol.utils.http_clients.assets_backend import (
    ReadPolicyEnumFactory,
    SharePolicyEnumFactory,
)
from youwol.utils.http_clients.assets_gateway import (
    AssetResponse,
    AssetWithPermissionResponse,
    GroupAccess,
    PermissionsResponse,
)


def to_asset_resp(
    asset, permissions: PermissionsResponse | None = None
) -> AssetResponse | AssetWithPermissionResponse:
    group_id = asset["groupId"] if "groupId" in asset else to_group_id(asset["scope"])
    if permissions:
        return AssetWithPermissionResponse(
            **{**asset, **{"groupId": group_id, "permissions": permissions}}
        )
    return AssetResponse(**{**asset, **{"groupId": group_id}})


def format_policy(policy: Any) -> GroupAccess:
    if policy["read"] not in ReadPolicyEnumFactory:
        raise RuntimeError("Read policy not known")

    if policy["share"] not in SharePolicyEnumFactory:
        raise RuntimeError("Share policy not known")

    expiration = None
    if policy["read"] == "expiration-date":
        deadline = policy["timestamp"] + policy["parameters"]["period"]
        expiration = str(datetime.fromtimestamp(deadline))

    return GroupAccess(
        read=ReadPolicyEnumFactory[policy["read"]],
        expiration=expiration,
        share=SharePolicyEnumFactory[policy["share"]],
    )


def raw_id_to_asset_id(raw_id) -> str:
    b = str.encode(raw_id)
    return base64.urlsafe_b64encode(b).decode()


class AssetImg(BaseModel):
    name: str
    content: bytes


class AssetMeta(BaseModel):
    name: str | None = None
    description: str | None = None
    images: list[AssetImg] | None = None  # name, bytes
    kind: str | None = None
    groupId: str | None = None
    tags: list[str] | None = None
    dynamic_fields: dict[str, str | float | int] | None = None
