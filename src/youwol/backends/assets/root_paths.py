# standard library
import asyncio
import itertools
import json
import time

# third parties
from fastapi import APIRouter, Depends
from fastapi import Query as RequestQuery
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
    private_group_id,
    to_group_id,
    to_group_scope,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import (
    AccessInfoResp,
    AccessPolicyBody,
    AccessPolicyResp,
    AssetResponse,
    ConsumerInfo,
    ExposingGroup,
    NewAssetBody,
    OwnerInfo,
    OwningGroup,
    PermissionsResp,
    PostAssetBody,
    ReadPolicyEnum,
    SharePolicyEnum,
)
from youwol.utils.types import AnyDict

# relative
from .routers import router_files, router_images, router_raw
from .utils import (
    access_policy_record_id,
    db_delete,
    db_get,
    db_post,
    format_asset,
    format_policy,
    get_asset_implementation,
    log_asset,
    to_doc_db_id,
    to_snake_case,
)

router = APIRouter(tags=["assets-backend"])
router.include_router(router_files)
router.include_router(router_images)
router.include_router(router_raw)

flatten = itertools.chain.from_iterable


@router.put("/assets", response_model=AssetResponse, summary="new asset")
async def create_asset(
    request: Request,
    body: NewAssetBody,
    configuration: Configuration = Depends(get_configuration),
) -> AssetResponse:
    """
    Creates a new asset.

    Parameters:
        request: Incoming request.
        body: Asset's properties.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The asset description.
    """
    async with Context.start_ep(request=request) as ctx:
        user = user_info(request)
        policy = body.defaultAccessPolicy
        asset_id = body.assetId if body.assetId else to_doc_db_id(body.rawId)
        owning_group = body.groupId or private_group_id(user)
        doc_asset = {
            "asset_id": asset_id,
            "related_id": body.rawId,
            "group_id": owning_group,
            "name": body.name,
            "description": body.description,
            "kind": body.kind,
            "tags": body.tags,
            "images": [],
            "thumbnails": [],
        }
        await db_post(doc=doc_asset, configuration=configuration, context=ctx)
        if (
            policy.read == ReadPolicyEnum.forbidden
            and policy.share == SharePolicyEnum.forbidden
        ):
            return format_asset(doc_asset, request)

        docdb_access = configuration.doc_db_access_policy
        now = time.time()  # s since epoch (January 1, 1970)
        doc_access_default = {
            "record_id": access_policy_record_id(asset_id, "*"),
            "asset_id": asset_id,
            "related_id": body.rawId,
            "consumer_group_id": "*",
            "read": body.defaultAccessPolicy.read.value,
            "share": body.defaultAccessPolicy.share.value,
            "parameters": "{}",
            "timestamp": int(now),
        }

        await docdb_access.create_document(
            doc=doc_access_default, owner=Constants.public_owner, headers=ctx.headers()
        )
        return format_asset(doc_asset, request)


@router.post(
    "/assets/{asset_id}", response_model=AssetResponse, summary="Updates an asset."
)
async def post_asset(
    request: Request,
    asset_id: str,
    body: PostAssetBody,
    configuration: Configuration = Depends(get_configuration),
) -> AssetResponse:
    """
    Updates an asset.

    Parameters:
        request: Incoming request.
        body: Asset's properties.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The asset description.
    """

    async with Context.start_ep(request=request) as ctx:
        docdb_access = configuration.doc_db_access_policy
        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )

        new_attributes = {
            to_snake_case(k): v for k, v in body.dict().items() if v is not None
        }
        if "group_id" in new_attributes and "/" in new_attributes["group_id"]:
            new_attributes["group_id"] = to_group_id(new_attributes["group_id"])

        doc = {**asset, **new_attributes}

        if "defaultAccessPolicy" in doc:
            #  access data are stored only in access_policy db
            del doc["defaultAccessPolicy"]

        await db_post(doc=doc, configuration=configuration, context=ctx)
        if body.defaultAccessPolicy:
            now = time.time()  # s since epoch (January 1, 1970)
            doc_access = {
                "record_id": access_policy_record_id(asset_id, "*"),
                "asset_id": asset_id,
                "related_id": asset["related_id"],
                "consumer_group_id": "*",
                "read": body.defaultAccessPolicy.read.value,
                "share": body.defaultAccessPolicy.share.value,
                "parameters": "{}",
                "timestamp": int(now),
            }
            await docdb_access.create_document(
                doc=doc_access, owner=Constants.public_owner, headers=ctx.headers()
            )

        return format_asset(doc, request)


async def put_access_policy_impl(
    asset_id: str,
    group_id: str,
    body: AccessPolicyBody,
    configuration: Configuration,
    context: Context,
):
    asset = await db_get(
        asset_id=asset_id, configuration=configuration, context=context
    )
    docdb_access = configuration.doc_db_access_policy
    now = time.time()  # s since epoch (January 1, 1970)
    doc_access = {
        "record_id": access_policy_record_id(asset_id, group_id),
        "asset_id": asset_id,
        "related_id": asset["related_id"],
        "consumer_group_id": group_id,
        "read": body.read.value,
        "share": body.share.value,
        "parameters": json.dumps(body.parameters),
        "timestamp": int(now),
    }
    await docdb_access.create_document(
        doc=doc_access, owner=Constants.public_owner, headers=context.headers()
    )

    return {}


@router.put(
    "/assets/{asset_id}/access/{group_id}",
    summary="Add access policy for a particular asset & group.",
)
async def put_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    body: AccessPolicyBody,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Adds access policy for a particular asset & group.

    Parameters:
        request: Incoming request.
        asset_id: target asset's ID.
        group_id: target group's ID.
        body: access policy.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Empty JSON response.
    """
    async with Context.start_ep(request=request) as ctx:
        return await put_access_policy_impl(
            asset_id=asset_id,
            group_id=group_id,
            body=body,
            configuration=configuration,
            context=ctx,
        )


@router.delete(
    "/assets/{asset_id}/access/{group_id}",
    summary="Delete access policy for a particular asset & group.",
)
async def delete_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Deletes access policy for a particular asset & group.

    Parameters:
        request: Incoming request.
        asset_id: target asset's ID.
        group_id: target group's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Empty JSON response.
    """
    async with Context.start_ep(request=request) as ctx:
        docdb_access = configuration.doc_db_access_policy
        await docdb_access.delete_document(
            doc={"asset_id": asset_id, "consumer_group_id": group_id},
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )
        return {}


@router.get(
    "/assets/{asset_id}/access/{group_id}",
    response_model=AccessPolicyResp,
    summary="Retrieves access policy for a particular asset & group.",
)
async def get_access_policy(
    request: Request,
    asset_id: str,
    group_id: str,
    include_inherited: bool = RequestQuery(True, alias="include-inherited"),
    configuration: Configuration = Depends(get_configuration),
) -> AccessPolicyResp:
    """
    Retrieves access policy for a particular asset & group.

    Parameters:
        request: Incoming request.
        asset_id: target asset's ID.
        group_id: target group's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Access policy description.
    """

    def query_body(for_group_id: str):
        return QueryBody(
            max_results=1,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id),
                    WhereClause(
                        column="consumer_group_id", relation="eq", term=for_group_id
                    ),
                ]
            ),
        )

    async with Context.start_ep(request=request) as ctx:
        docdb_access = configuration.doc_db_access_policy

        if not include_inherited:
            query_specific = query_body(for_group_id=group_id)
            resp = await docdb_access.query(
                query_body=query_specific,
                owner=Constants.public_owner,
                headers=ctx.headers(),
            )
            if not resp["documents"]:
                raise QueryIndexException(
                    query="docdb_access@[asset_id,group_id]",
                    error={
                        "reason": "no record found",
                        "assetId": asset_id,
                        "groupId": group_id,
                    },
                )
            doc = resp["documents"][0]
            return AccessPolicyResp(
                read=ReadPolicyEnum[doc["read"]],
                parameters=json.loads(doc["parameters"]),
                share=SharePolicyEnum[doc["share"]],
                timestamp=doc["timestamp"],
            )

        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        if is_child_group(child_group_id=group_id, parent_group_id=asset["group_id"]):
            return AccessPolicyResp(
                read=ReadPolicyEnum.owning,
                parameters={},
                share=SharePolicyEnum.authorized,
                timestamp=None,
            )

        ancestors_groups = [group_id] + ancestors_group_id(group_id)
        bodies_specific = [
            query_body(for_group_id=for_group_id) for for_group_id in ancestors_groups
        ]

        query_specific = [
            docdb_access.query(
                query_body=body, owner=Constants.public_owner, headers=ctx.headers()
            )
            for body in bodies_specific
        ]

        body_default = query_body(for_group_id="*")

        query_default = docdb_access.query(
            query_body=body_default, owner=Constants.public_owner, headers=ctx.headers()
        )

        *specifics, default = await asyncio.gather(*query_specific, query_default)
        closed = {
            "read": "forbidden",
            "parameters": "{}",
            "timestamp": -1,
            "share": "forbidden",
        }
        documents = (
            list(flatten([s["documents"] for s in specifics]))
            + default["documents"]
            + [closed]
        )
        if not documents:
            return AccessPolicyResp(
                read=ReadPolicyEnum.forbidden,
                parameters={},
                share=SharePolicyEnum.forbidden,
                timestamp=None,
            )

        doc = documents[0]
        return AccessPolicyResp(
            read=ReadPolicyEnum[doc["read"]],
            parameters=json.loads(doc["parameters"]),
            share=SharePolicyEnum[doc["share"]],
            timestamp=doc["timestamp"],
        )


def get_permission(write, policies):
    if not policies:
        return PermissionsResp(write=False, read=False, share=False, expiration=None)

    opened = any(policy["read"] == ReadPolicyEnum.authorized for policy in policies)
    share = any(policy["share"] == SharePolicyEnum.authorized for policy in policies)
    if opened:
        return PermissionsResp(write=write, read=True, share=share, expiration=None)

    deadlines = [
        policy
        for policy in policies
        if policy["read"] == ReadPolicyEnum.expiration_date
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
        and default["documents"][0]["read"] == ReadPolicyEnum.authorized
        and default["documents"][0]["share"] == SharePolicyEnum.authorized
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


@router.delete("/assets/{asset_id}", summary="Delete an asset.")
async def delete_asset(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Deletes an asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Empty JSON.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        await log_asset(asset=asset, context=ctx)
        docdb_access = configuration.doc_db_access_policy

        query = QueryBody(
            max_results=1000,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id)
                ]
            ),
        )

        _, docs = await asyncio.gather(
            db_delete(asset=asset, configuration=configuration, context=ctx),
            docdb_access.query(
                query_body=query, owner=Constants.public_owner, headers=ctx.headers()
            ),
        )
        await ctx.info("Found access records for the asset", data={"records": docs})
        await asyncio.gather(
            *[
                docdb_access.delete_document(
                    doc=d, owner=Constants.public_owner, headers=ctx.headers()
                )
                for d in docs["documents"]
            ]
        )
        filesystem = configuration.file_system

        root_path = f"{asset['kind']}/{asset_id}/"
        await ctx.info(f"Delete associated objects from {root_path}")
        objects = await filesystem.list_objects(prefix=root_path, recursive=True)
        for obj in objects:
            path = obj.object_id
            await ctx.info(text=f"Delete file @ {path}")
            await filesystem.remove_object(object_id=path)

        return {}


@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    summary="Retrieves general asset information.",
)
async def get_asset(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AssetResponse:
    """
    Retrieves general asset information.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The asset description.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await get_asset_implementation(
            request=request, asset_id=asset_id, configuration=configuration, context=ctx
        )
