# standard library
import asyncio
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
    is_child_group,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import (
    AccessPolicyBody,
    AccessPolicyResp,
    ReadPolicyEnum,
    ReadPolicyEnumFactory,
    SharePolicyEnum,
    SharePolicyEnumFactory,
)
from youwol.utils.types import AnyDict

# relative
from ..utils import access_policy_record_id, db_get, flatten

router = APIRouter(tags=["assets-backend.access"])


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
                read=ReadPolicyEnumFactory[doc["read"]],
                parameters=json.loads(doc["parameters"]),
                share=SharePolicyEnumFactory[doc["share"]],
                timestamp=doc["timestamp"],
            )

        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        if is_child_group(child_group_id=group_id, parent_group_id=asset["group_id"]):
            return AccessPolicyResp(
                read=ReadPolicyEnum.OWNING,
                parameters={},
                share=SharePolicyEnum.AUTHORIZED,
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
                read=ReadPolicyEnum.FORBIDDEN,
                parameters={},
                share=SharePolicyEnum.FORBIDDEN,
                timestamp=None,
            )

        doc = documents[0]
        return AccessPolicyResp(
            read=ReadPolicyEnumFactory[doc["read"]],
            parameters=json.loads(doc["parameters"]),
            share=SharePolicyEnumFactory[doc["share"]],
            timestamp=doc["timestamp"],
        )
