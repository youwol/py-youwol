# standard library
import io
import tempfile
import zipfile

from pathlib import Path
from zipfile import ZipFile

# third parties
from fastapi import APIRouter, Depends, File, UploadFile
from starlette.requests import Request
from starlette.responses import Response

# Youwol utilities
from youwol.utils import extract_bytes_ranges, get_content_type
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import AddFilesResponse
from youwol.utils.types import AnyDict

# relative
from ..configurations import Configuration, get_configuration
from ..utils import db_get, get_file_path, log_asset

router = APIRouter(tags=["assets-backend.files"])


@router.post("/assets/{asset_id}/files", response_model=AddFilesResponse)
async def add_zip_files(
    request: Request,
    asset_id: str,
    file: UploadFile = File(...),
    configuration: Configuration = Depends(get_configuration),
) -> AddFilesResponse:
    """
    Associates files (using a .zip file) to an asset.
    The files are extracted in the youwol filesystem, preserving the files organization coming from the zip.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        file: the zip file.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        Files upload description.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        await log_asset(asset=asset, context=ctx)
        filesystem = configuration.file_system
        await filesystem.ensure_bucket()
        content = await file.read()
        io_stream = io.BytesIO(content)
        input_zip = ZipFile(io_stream)
        items = {name: input_zip.read(name) for name in input_zip.namelist()}
        files = {name: content for name, content in items.items() if name[-1] != "/"}

        await ctx.info(
            text="Zip file decoded successfully", data={"paths": list(files.keys())}
        )

        for path, content in files.items():
            await filesystem.put_object(
                object_id=get_file_path(
                    asset_id=asset_id, kind=asset["kind"], file_path=path
                ),
                data=io.BytesIO(content),
                object_name=Path(path).name,
                content_type=get_content_type(path),
                content_encoding="identity",
            )
        return AddFilesResponse(filesCount=len(files), totalBytes=len(content))


@router.get("/assets/{asset_id}/files/{rest_of_path:path}")
async def get_file(
    request: Request,
    asset_id: str,
    rest_of_path: str,
    configuration: Configuration = Depends(get_configuration),
) -> Response:
    """
    Retrieves a file associated to an asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        rest_of_path: Path to the file.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The file content.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        await log_asset(asset=asset, context=ctx)
        path = get_file_path(
            asset_id=asset_id, kind=asset["kind"], file_path=rest_of_path
        )
        await ctx.info(text=f"Recover object at {path}")
        filesystem = configuration.file_system
        stats = await filesystem.get_info(object_id=path)
        ranges_bytes = extract_bytes_ranges(request=request)
        content = await filesystem.get_object(object_id=path, ranges_bytes=ranges_bytes)
        await ctx.info("Retrieved object", data={"stats": stats, "size": len(content)})
        return Response(
            status_code=206 if ranges_bytes else 200,
            content=content,
            media_type=stats["metadata"]["contentType"],
            headers={
                "Content-Encoding": stats["metadata"]["contentEncoding"],
                "cache-control": "public, max-age=0",
            },
        )


@router.delete("/assets/{asset_id}/files")
async def delete_files(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Deletes all files associated to an asset.

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
        filesystem = configuration.file_system
        await filesystem.remove_folder(
            prefix=get_file_path(asset_id=asset_id, kind=asset["kind"], file_path=""),
            raise_not_found=True,
        )
        return {}


@router.get("/assets/{asset_id}/files")
async def get_zip_files(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> Response:
    """
    Retrieves all the files associated to an asset in a zip file..

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The zip file..
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        await log_asset(asset=asset, context=ctx)
        filesystem = configuration.file_system
        base_arc_name = get_file_path(
            asset_id=asset_id, kind=asset["kind"], file_path=""
        )
        objects = await filesystem.list_objects(prefix=base_arc_name, recursive=True)
        await ctx.info(text="Objects list iterators retrieved successfully")
        with tempfile.TemporaryDirectory() as tmp_folder:
            base_path = Path(tmp_folder)
            with zipfile.ZipFile(
                base_path / "asset_files.zip", "w", zipfile.ZIP_DEFLATED
            ) as zipper:
                for obj in objects:
                    path = obj.object_id
                    await ctx.info(text=f"Zip file {path}")
                    content = await filesystem.get_object(object_id=path)
                    (base_path / path).parent.mkdir(exist_ok=True, parents=True)
                    with open(base_path / path, "wb") as fp:
                        fp.write(content)
                    arc_name = Path(path).relative_to(base_arc_name)
                    zipper.write(base_path / path, arcname=arc_name)

            content = (Path(tmp_folder) / "asset_files.zip").read_bytes()
            return Response(content=content, media_type="application/zip")
