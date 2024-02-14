# standard library
import asyncio
import json
import time

# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request

# Youwol backends
from youwol.backends.assets.configurations import (
    Configuration,
    Constants,
    get_configuration,
)

# Youwol utilities
from youwol.utils import (
    Query,
    QueryBody,
    QueryIndexException,
    WhereClause,
    ancestors_group_id,
    get_leaf_group_ids,
    is_child_group,
    to_group_scope,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import (
    AccessInfoResp,
    ConsumerInfo,
    ExposingGroup,
    OwnerInfo,
    OwningGroup,
    PermissionsResp,
    ReadPolicyEnum,
    SharePolicyEnum,
)

# relative
from ..utils import db_get, flatten, format_policy, get_asset_implementation
from .access import get_access_policy

router = APIRouter(tags=["assets-backend.permissions"])


def get_permission(write, policies):
    if not policies:
        return PermissionsResp(write=False, read=False, share=False, expiration=None)

    opened = any(policy["read"] == ReadPolicyEnum.AUTHORIZED for policy in policies)
    share = any(policy["share"] == SharePolicyEnum.AUTHORIZED for policy in policies)
    if opened:
        return PermissionsResp(write=write, read=True, share=share, expiration=None)

    deadlines = [
        policy
        for policy in policies
        if policy["read"] == ReadPolicyEnum.EXPIRATION_DATE
    ]
    if deadlines:
        expirations = [
            policy["timestamp"] + json.loads(policy["parameters"])["period"]
            for policy in deadlines
        ]
        remaining = max(expirations) - int(time.time())
        return PermissionsResp(
            write=write, read=remaining > 0, share=share, expiration=remaining
        )

    return PermissionsResp(write=write, read=False, share=False, expiration=None)


async def get_permissions_implementation(
    request: Request, asset_id: str, configuration: Configuration, context: Context
) -> PermissionsResp:
    user = user_info(request)
    group_ids = get_leaf_group_ids(user)
    group_ids = list(
        flatten([[group_id] + ancestors_group_id(group_id) for group_id in group_ids])
    )
    group_ids = list(set(group_ids))

    asset = await db_get(
        asset_id=asset_id, configuration=configuration, context=context
    )
    #  watch for owner case with read access
    if any(
        is_child_group(child_group_id=group_id, parent_group_id=asset["group_id"])
        for group_id in group_ids
    ):
        return PermissionsResp(write=True, read=True, share=True, expiration=None)

    # watch if default policy is sufficient
    docdb_access = configuration.doc_db_access_policy

    body_default = QueryBody(
        max_results=1,
        query=Query(
            where_clause=[
                WhereClause(column="asset_id", relation="eq", term=asset_id),
                WhereClause(column="consumer_group_id", relation="eq", term="*"),
            ]
        ),
    )

    default = await docdb_access.query(
        query_body=body_default, owner=Constants.public_owner, headers=context.headers()
    )

    if (
        len(default["documents"]) > 0
        and default["documents"][0]["read"] == ReadPolicyEnum.AUTHORIZED
        and default["documents"][0]["share"] == SharePolicyEnum.AUTHORIZED
    ):
        return PermissionsResp(write=False, read=True, share=True, expiration=None)

    # then gather specific policies for the all the groups the user belongs
    bodies_specific = [
        QueryBody(
            max_results=1,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id),
                    WhereClause(
                        column="consumer_group_id", relation="eq", term=group_id
                    ),
                ]
            ),
        )
        for group_id in group_ids
    ]

    specifics = await asyncio.gather(
        *[
            docdb_access.query(
                query_body=body, owner=Constants.public_owner, headers=context.headers()
            )
            for body in bodies_specific
        ]
    )
    policies = list(flatten([d["documents"] for d in specifics]))
    permission = get_permission(False, policies)

    return permission


@router.get(
    "/assets/{asset_id}/permissions",
    response_model=PermissionsResp,
    summary="    Retrieves the permissions of the user regarding access on a particular asset.",
)
async def get_permissions(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> PermissionsResp:
    """
    Retrieves the permissions of the user regarding access on a particular asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Permissions description.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await get_permissions_implementation(
            request=request, asset_id=asset_id, configuration=configuration, context=ctx
        )


@router.get(
    "/assets/{asset_id}/access-info",
    response_model=AccessInfoResp,
    summary="Summarize access information on a particular asset.",
)
async def access_info(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AccessInfoResp:
    """
    Summarizes access information on a particular asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Access summary.
    """
    max_policies_count = 1000
    async with Context.start_ep(
        request=request,
        with_attributes={"asset_id": asset_id},
    ) as ctx:
        docdb_access = configuration.doc_db_access_policy
        body_default = QueryBody(
            max_results=max_policies_count,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id)
                ]
            ),
        )

        policies = await docdb_access.query(
            query_body=body_default, owner=Constants.public_owner, headers=ctx.headers()
        )
        if len(policies["documents"]) > max_policies_count:
            raise QueryIndexException(
                query="access_policy, query policies by asset_id",
                error=f"Maximum expected count reached {max_policies_count}",
            )

        asset, permissions = await asyncio.gather(
            get_asset_implementation(
                request=request,
                asset_id=asset_id,
                configuration=configuration,
                context=ctx,
            ),
            get_permissions_implementation(
                request=request,
                asset_id=asset_id,
                configuration=configuration,
                context=ctx,
            ),
        )
        owning_group = OwningGroup(
            name=to_group_scope(asset.groupId), groupId=asset.groupId
        )

        groups = list(
            {
                policy["consumer_group_id"]
                for policy in policies["documents"]
                if policy["consumer_group_id"] != asset.groupId
            }
        )
        policies_groups = await asyncio.gather(
            *[
                get_access_policy(
                    request=request,
                    asset_id=asset_id,
                    group_id=group_id,
                    configuration=configuration,
                )
                for group_id in groups + ["*"]
            ]
        )
        exposing_groups = [
            ExposingGroup(
                name=to_group_scope(group), groupId=group, access=format_policy(policy)
            )
            for group, policy in zip(groups, policies_groups[0:-1])
            if group != "*"
        ]
        default_access = format_policy(policies_groups[-1])
        owner_info = OwnerInfo(
            exposingGroups=exposing_groups, defaultAccess=default_access
        )

        permissions = PermissionsResp(
            write=permissions.write,
            read=permissions.read,
            share=permissions.share,
            expiration=permissions.expiration,
        )

        consumer_info = ConsumerInfo(permissions=permissions)

        return AccessInfoResp(
            owningGroup=owning_group, ownerInfo=owner_info, consumerInfo=consumer_info
        )
