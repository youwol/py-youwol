import json

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils.context import Context
from ..configurations import Configuration, get_configuration
from ..raw_stores.interface import AssetMeta
from ..utils import raw_id_to_asset_id

router = APIRouter()


async def get_raw_generic(
        request: Request,
        kind: str,
        raw_id: str,
        rest_of_the_path,
        configuration: Configuration
):
    async with Context.start_ep(
            request=request,
            action='get raw part of asset',
            with_attributes={"kind": kind, 'rawId': raw_id, "restOfPath": rest_of_the_path or ""}
    ) as ctx:

        headers = ctx.headers()
        assets_stores = configuration.assets_stores()
        assets_db = configuration.assets_client
        store = next(store for store in assets_stores if kind == store.path_name)

        asset_id = raw_id_to_asset_id(raw_id)
        permissions = await assets_db.get_permissions(asset_id=asset_id, headers=ctx.headers())
        if not permissions['read']:
            raise HTTPException(status_code=401, detail="Asset not accessible")

        raw = await store.get_asset(request=request, raw_id=raw_id, rest_of_path=rest_of_the_path, headers=headers)

        #  asyncio.ensure_future(assets_db.record_access(raw_id=raw_id, headers=headers))

        headers_resp = {'content-type': 'application/json'} if not isinstance(raw, Response) else raw.headers
        if permissions['expiration']:
            headers_resp["cache-control"] = 'private, max-age=' + str(permissions['expiration'])

        content = json.dumps(raw) if not isinstance(raw, Response) else raw.body
        return Response(content=content, headers=headers_resp)


async def get_raw_metadata_generic(
        request: Request,
        kind: str,
        raw_id: str,
        configuration: Configuration,
        rest_of_the_path=None
):
    async with Context.start_ep(
            request=request,
            action='get raw metadata',
            with_attributes={"kind": kind, 'rawId': raw_id, "restOfPath": rest_of_the_path or ""}
    ) as ctx:
        assets_stores = configuration.assets_stores()
        store = next(store for store in assets_stores if kind == store.path_name)

        meta = await store.get_asset_metadata(request=request, raw_id=raw_id, rest_of_path=rest_of_the_path,
                                              headers=ctx.headers())
        return meta


@router.get("/{raw_id}/asset",
            summary="get an asset")
async def get_asset_by_raw_id(
        request: Request,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            action="get asset from raw record's id",
            request=request,
            with_attributes={'rawId': raw_id}
    ) as ctx:
        headers = ctx.headers()
        assets_db = configuration.assets_client
        body = {"whereClauses": [{"column": "related_id", "relation": "eq", "term": raw_id}]}
        query_result = await assets_db.query(body=body, headers=headers)
        if not query_result['assets']:
            raise HTTPException(status_code=404, detail="Asset not found")
        asset = query_result['assets'][0]
        return asset


@router.get("/{kind}/metadata/{raw_id}",
            summary="get raw record")
async def get_raw_metadata(
        request: Request,
        kind: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_raw_metadata_generic(request=request, kind=kind, raw_id=raw_id,
                                          configuration=configuration, rest_of_the_path="")


@router.get("/{kind}/metadata/{raw_id}/{rest_of_path:path}",
            summary="get raw record")
async def get_raw_metadata(
        request: Request,
        kind: str,
        rest_of_path: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_raw_metadata_generic(request=request, kind=kind, raw_id=raw_id, rest_of_the_path=rest_of_path,
                                          configuration=configuration)


@router.get("/{kind}/{raw_id}",
            summary="get raw record")
async def get_raw(
        request: Request,
        kind: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_raw_generic(request=request, kind=kind, raw_id=raw_id, rest_of_the_path=None,
                                 configuration=configuration)


@router.get("/{kind}/{raw_id}/{rest_of_path:path}",
            summary="get raw record")
async def get_raw(
        request: Request,
        kind: str,
        rest_of_path: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_raw_generic(request=request, kind=kind, raw_id=raw_id, rest_of_the_path=rest_of_path,
                                 configuration=configuration)


async def update_raw_asset_generic(
        request: Request,
        kind: str,
        raw_id: str,
        rest_of_path,
        configuration: Configuration
):
    async with Context.start_ep(
            request=request,
            action="update raw part of asset",
            with_attributes={"kind": kind, "rawId": raw_id, "rest_of_path": rest_of_path}
    ) as ctx:
        headers = ctx.headers()
        assets_stores = configuration.assets_stores()
        store = next(store for store in assets_stores if kind == store.path_name)
        asset_id = raw_id_to_asset_id(raw_id)
        asset = await configuration.assets_client.get(asset_id=asset_id, headers=headers)

        meta = AssetMeta(name=asset["name"], description=asset["description"], kind=kind, groupId=asset["groupId"],
                         tags=asset['tags']
                         )
        await ctx.info("Metadata", data=meta)
        resp = await store.update_asset(request=request, raw_id=raw_id, metadata=meta, rest_of_path=rest_of_path,
                                        headers=headers)
        return resp


@router.post("/{kind}/{raw_id}",
             summary="update the raw part of an asset")
async def update_raw_asset(
        request: Request,
        kind: str,
        raw_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await update_raw_asset_generic(request=request, kind=kind, raw_id=raw_id, rest_of_path="",
                                          configuration=configuration)


@router.post("/{kind}/{raw_id}/{rest_of_path:path}",
             summary="update the raw part of an asset")
async def update_raw_asset(
        request: Request,
        kind: str,
        raw_id: str,
        rest_of_path: str,
        configuration: Configuration = Depends(get_configuration)):
    return await update_raw_asset_generic(request=request, kind=kind, raw_id=raw_id, rest_of_path=rest_of_path,
                                          configuration=configuration)
