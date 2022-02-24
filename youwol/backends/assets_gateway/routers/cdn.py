from typing import List, Tuple, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from youwol_utils import (HTTPException)
from youwol_utils.context import Context
from ..configurations import Configuration, get_configuration
from ..utils import raw_id_to_asset_id

router = APIRouter()


class Library(BaseModel):
    name: str
    version: str
    id: str
    namespace: str
    type: str


Url = str


class LoadingGraphResponseV1(BaseModel):
    graphType: str
    lock: List[Library]
    definition: List[List[Tuple[str, Url]]]


class LoadingGraphBody(BaseModel):
    libraries: Dict[str, str]
    using: Dict[str, str] = {}


async def ensure_permission(
        permission: str,
        library_name: str,
        configuration: Configuration,
        context: Context):
    async with context.start(
            action='ensure permission',
            with_attributes={"library_name": library_name}
    ) as ctx:
        asset_id = raw_id_to_asset_id(library_name)
        asset_id = raw_id_to_asset_id(asset_id)

        assets_db = configuration.assets_client
        permissions = await assets_db.get_permissions(asset_id=asset_id, headers=ctx.headers())
        if not permissions[permission]:
            raise HTTPException(status_code=401, detail=f"Unauthorized to access {library_name}")


@router.post("/queries/loading-graph",
             summary="describes the loading graph of provided libraries",
             response_model=LoadingGraphResponseV1)
async def resolve_loading_tree(
        request: Request,
        body: LoadingGraphBody,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[LoadingGraphResponseV1]
    async with Context.start_ep(
            action='resolve loading tree',
            request=request,
            body=body,
            response=lambda: response
    ) as ctx:
        response = await configuration.cdn_client.query_loading_graph(body=body.dict(), headers=ctx.headers())
        return response


async def delete_version_generic(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration):
    response = Optional[LoadingGraphResponseV1]
    async with Context.start_ep(
            action='delete package version',
            request=request,
            response=lambda: response,
            with_attributes={"libraryName": library_name, version: 'version'}
    ) as ctx:
        await ensure_permission(permission='write', library_name=library_name, configuration=configuration, context=ctx)
        cdn_client = configuration.cdn_client
        return await cdn_client.delete_version(library_name=library_name, version=version, headers=ctx.headers())


@router.delete("/libraries/{namespace}/{library_name}/{version}", summary="delete a specific version")
async def delete_version_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):
    return await delete_version_generic(request=request, library_name=f"{namespace}/{library_name}",
                                        version=version, configuration=configuration)


@router.delete("/libraries/{library_name}/{version}", summary="delete a specific version")
async def delete_version_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):
    return await delete_version_generic(request=request, library_name=library_name,
                                        version=version, configuration=configuration)


async def get_package_generic(
        request: Request,
        library_name: str,
        version: str,
        metadata: bool,
        configuration: Configuration):
    response = Optional[LoadingGraphResponseV1]
    async with Context.start_ep(
            action=f'get package ({"metadata" if metadata else "raw content"})',
            request=request,
            response=lambda: response,
            with_attributes={"libraryName": library_name, version: 'version'}
    ) as ctx:
        await ensure_permission(permission='read', library_name=library_name, configuration=configuration, context=ctx)

        cdn_client = configuration.cdn_client
        resp = await cdn_client.get_package(library_name=library_name, version=version, metadata=metadata,
                                            headers=ctx.headers())
        return JSONResponse(resp) \
            if metadata \
            else Response(resp, media_type='multipart/form-data')


@router.get("/libraries/{namespace}/{library_name}/{version}", summary="delete a specific version")
async def get_package_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        metadata: bool = False,
        configuration: Configuration = Depends(get_configuration)):
    return await get_package_generic(request=request, library_name=f"{namespace}/{library_name}",
                                     version=version, metadata=metadata, configuration=configuration)


@router.get("/libraries/{library_name}/{version}", summary="delete a specific version")
async def get_package_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        metadata: bool = False,
        configuration: Configuration = Depends(get_configuration)):
    return await get_package_generic(request=request, library_name=library_name,
                                     version=version, metadata=metadata, configuration=configuration)
