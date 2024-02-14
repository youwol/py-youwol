# standard library
import asyncio
import time
import uuid

# third parties
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as RequestQuery
from starlette.requests import Request

# Youwol backends
from youwol.backends.assets.configurations import (
    Configuration,
    Constants,
    get_configuration,
)

# Youwol utilities
from youwol.utils import Query, QueryBody, WhereClause, user_info
from youwol.utils.context import Context

# relative
from ..utils import format_record_history

router = APIRouter(tags=["assets-backend"])


@router.put("/raw/access/{related_id}", summary="register access")
async def record_access(
    request: Request,
    related_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    # WARNING: use 'allow_filtering' => do not use in prod
    # Probably need as secondary index on 'related_id'

    async with Context.start_ep(request=request) as ctx:  # type: Context
        user = user_info(request)
        doc_db_assets, doc_db_history = (
            configuration.doc_db_asset,
            configuration.doc_db_access_history,
        )

        query = QueryBody(
            max_results=1,
            allow_filtering=True,
            query=Query(
                where_clause=[
                    WhereClause(column="related_id", relation="eq", term=related_id)
                ]
            ),
        )
        asset = await doc_db_assets.query(
            query_body=query, owner=Constants.public_owner, headers=ctx.headers()
        )

        if len(asset["documents"]) == 0:
            raise HTTPException(
                status_code=404, detail=f"Asset with related_id ${related_id} not found"
            )
        if len(asset["documents"]) > 1:
            raise HTTPException(
                status_code=404,
                detail=f"Multiple assets with related_id ${related_id} found",
            )

        asset = asset["documents"][0]
        now = time.time()  # s since epoch (January 1, 1970)
        doc = {
            "record_id": str(uuid.uuid4()),
            "asset_id": asset["asset_id"],
            "related_id": asset["related_id"],
            "username": user["preferred_username"],
            "timestamp": int(now),
        }
        await doc_db_history.create_document(
            doc=doc, owner=Constants.public_owner, headers=ctx.headers()
        )

        return doc


@router.get("/raw/access/{asset_id}/query-latest", summary="query latest access record")
async def query_access(
    request: Request,
    asset_id,
    max_count: int = RequestQuery(100, alias="max-count"),
    configuration: Configuration = Depends(get_configuration),
):
    # WARNING: use 'allow_filtering' => do not use in prod
    # Probably need as secondary index on 'related_id'

    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db_history = configuration.doc_db_access_history

        query = QueryBody(
            max_results=max_count,
            allow_filtering=True,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id)
                ]
            ),
        )

        results = await doc_db_history.query(
            query_body=query, owner=Constants.public_owner, headers=ctx.headers()
        )

        return {"records": [format_record_history(r) for r in results["documents"]]}


@router.delete("/raw/access/{asset_id}", summary="clear user access history")
async def clear_asset_history(
    request: Request,
    asset_id,
    count: int = 1000,
    configuration: Configuration = Depends(get_configuration),
):
    # WARNING: use 'allow_filtering' => do not use in prod
    # Probably need as secondary index on 'related_id'

    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db_history = configuration.doc_db_access_history

        user = user_info(request)
        query = QueryBody(
            max_results=count,
            allow_filtering=True,
            query=Query(
                where_clause=[
                    WhereClause(column="asset_id", relation="eq", term=asset_id),
                    WhereClause(
                        column="username",
                        relation="eq",
                        term=user["preferred_username"],
                    ),
                ]
            ),
        )

        results = await doc_db_history.query(
            query_body=query, owner=Constants.public_owner, headers=ctx.headers()
        )
        await asyncio.gather(
            *[
                doc_db_history.delete_document(
                    doc=doc, owner=Constants.public_owner, headers=ctx.headers()
                )
                for doc in results["documents"]
            ]
        )
        return {}
