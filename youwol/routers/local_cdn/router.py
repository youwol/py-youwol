import os
import shutil
from itertools import groupby

from starlette.requests import Request
from fastapi import APIRouter, WebSocket, Depends

from utils_low_level import start_web_socket
from youwol.context import Context
from youwol.models import ActionStep
from youwol.routers.local_cdn.messages import send_status, send_details
from youwol.routers.local_cdn.models import PackagesStatus, Package, PackageVersion, VersionDetails, PackageDetails
from youwol.utils_paths import parse_json, write_json
from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.web_socket import WebSocketsCache
router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.local_cdn = ws
    await ws.send_json({})
    await start_web_socket(ws)


@router.get("/status",
            summary="local cdn status",
            response_model=PackagesStatus
            )
async def status(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.local_cdn)

    data = parse_json(config.pathsBook.local_cdn_docdb)['documents']
    data = sorted(data, key=lambda lib: lib["library_name"])
    data = groupby(data, key=lambda lib: lib["library_name"])
    packages = []
    for name, versions in data:
        versions = [PackageVersion(version=v["version"], versionNumber=v["version_number"]) for v in versions]
        versions = sorted(versions, key=lambda c: c.versionNumber)
        versions.reverse()
        package = Package(
            name=name,
            versions=versions
            )
        packages.append(package)

    cdn_status = PackagesStatus(packages=packages)
    await send_status(cdn_status=cdn_status, context=context)
    return cdn_status


async def package_details_generic(
        request: Request,
        package_name: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.local_cdn)

    data = parse_json(config.pathsBook.local_cdn_docdb)['documents']
    data = [d for d in data if d["library_name"] == package_name]

    def format_version(doc):
        storage_cdn_path = config.pathsBook.local_cdn_storage
        folder_path = storage_cdn_path / doc['path']
        bundle_path = folder_path / doc['bundle']
        files_count = sum([len(files) for r, d, files in os.walk(folder_path)])
        bundle_size = bundle_path.stat().st_size
        return VersionDetails(name=doc['library_name'], version=doc['version'], versionNumber=doc['version_number'],
                              filesCount=files_count, bundleSize=bundle_size)

    versions = [format_version(d) for d in data]
    package_details = PackageDetails(name=package_name, versions=versions)
    await send_details(package_details=package_details, context=context)

    return package_details


@router.get("/packages/{package_name}",
            summary="modules status",
            response_model=PackageDetails
            )
async def package_details_no_namespace(
        request: Request,
        package_name: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    return await package_details_generic(request=request, package_name=package_name, config=config)


@router.get("/packages/{namespace}/{package_name}",
            summary="modules status",
            response_model=PackageDetails
            )
async def package_details_with_namespace(
        request: Request,
        namespace: str,
        package_name: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    return await package_details_generic(request=request, package_name=namespace+'/'+package_name, config=config)


async def delete_library_generic(
        request: Request,
        package_name: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.local_cdn)

    async with context.start(action=f"Delete {package_name}@{version}") as ctx:
        await ctx.info(step=ActionStep.RUNNING, content=f"Delete {package_name}@{version}", json={})
        data = parse_json(config.pathsBook.local_cdn_docdb)['documents']
        doc = next(d for d in data if d["library_name"] == package_name and d['version'] == version)
        remaining = [d for d in data if not (d["library_name"] == package_name and d['version'] == version)]

        storage_cdn_path = config.pathsBook.local_cdn_storage
        folder_path = storage_cdn_path / doc['path']
        shutil.rmtree(folder_path)
        write_json(data={"documents": remaining}, path=config.pathsBook.local_cdn_docdb)
        details = await package_details_generic(request=request, package_name=package_name, config=config)
        return details


@router.delete("/libraries/{package_name}/{version}",
               summary="modules status",
               response_model=PackageDetails
               )
async def delete_version_no_namespace(
        request: Request,
        package_name: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    return await delete_library_generic(request=request, package_name=package_name, version=version, config=config)


@router.delete("/libraries/{namespace}/{package_name}/{version}",
               summary="modules status",
               response_model=PackageDetails
               )
async def delete_version_with_namespace(
        request: Request,
        namespace: str,
        package_name: str,
        version: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    return await delete_library_generic(request=request, package_name=namespace+'/'+package_name,
                                        version=version, config=config)

