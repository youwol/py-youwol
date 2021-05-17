from typing import List, Tuple, Dict

from fastapi import APIRouter, Depends

from pydantic import BaseModel

from starlette.requests import Request
from starlette.responses import Response

from ..configurations import Configuration, get_configuration

from ..utils import raw_id_to_asset_id

from youwol_utils import (generate_headers_downstream, HTTPException)

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
        request: Request,
        library_name: str,
        configuration: Configuration):

    headers = generate_headers_downstream(request.headers)
    asset_id = raw_id_to_asset_id(library_name)
    asset_id = raw_id_to_asset_id(asset_id)

    assets_db = configuration.assets_client
    permissions = await assets_db.get_permissions(asset_id=asset_id, headers=headers)
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
    headers = generate_headers_downstream(request.headers)
    resp = await configuration.cdn_client.query_loading_graph(body=body.dict(), headers=headers)
    return resp


async def delete_version_generic(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration):

    headers = generate_headers_downstream(request.headers)
    await ensure_permission('write', request, library_name, configuration)

    cdn_client = configuration.cdn_client
    return await cdn_client.delete_version(library_name=library_name, version=version, headers=headers)


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
        configuration: Configuration):

    headers = generate_headers_downstream(request.headers)
    await ensure_permission('read', request, library_name, configuration)

    cdn_client = configuration.cdn_client
    resp = await cdn_client.get_package(library_name=library_name, version=version, headers=headers)
    return Response(resp, media_type='multipart/form-data')


@router.get("/libraries/{namespace}/{library_name}/{version}", summary="delete a specific version")
async def get_package_with_namespace(
        request: Request,
        namespace: str,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):

    return await get_package_generic(request=request, library_name=f"{namespace}/{library_name}",
                                     version=version, configuration=configuration)


@router.get("/libraries/{library_name}/{version}", summary="delete a specific version")
async def get_package_no_namespace(
        request: Request,
        library_name: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):

    return await get_package_generic(request=request, library_name=library_name,
                                     version=version, configuration=configuration)

