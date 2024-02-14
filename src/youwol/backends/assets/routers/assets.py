# standard library
import asyncio
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
    WhereClause,
    private_group_id,
    to_group_id,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import (
    AssetResponse,
    NewAssetBody,
    PostAssetBody,
    ReadPolicyEnum,
    SharePolicyEnum,
)
from youwol.utils.types import AnyDict

# relative
from ..utils import (
    access_policy_record_id,
    db_delete,
    db_get,
    db_post,
    format_asset,
    get_asset_implementation,
    log_asset,
    to_doc_db_id,
    to_snake_case,
)

router = APIRouter(tags=["assets-backend.assets"])


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
            policy.read == ReadPolicyEnum.FORBIDDEN
            and policy.share == SharePolicyEnum.FORBIDDEN
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
