# standard library
import asyncio

from pathlib import Path

# third parties
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.requests import Request
from starlette.responses import Response

# Youwol backends
from youwol.backends.assets.configurations import (
    Configuration,
    Constants,
    get_configuration,
)

# Youwol utilities
from youwol.utils import FileData
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend import AssetResponse

# relative
from ..utils import (
    db_get,
    db_post,
    format_image,
    get_asset_implementation,
    get_thumbnail,
)

router = APIRouter(tags=["assets-backend"])


@router.post(
    "/assets/{asset_id}/images/{filename}",
    response_model=AssetResponse,
    summary="Add an image to an asset.",
)
async def post_image(
    request: Request,
    asset_id: str,
    filename: str,
    file: UploadFile = File(...),
    configuration: Configuration = Depends(get_configuration),
) -> AssetResponse:
    """
    Adds an image to an asset. A thumbnail 200px*200px is also created.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        filename: Name of the image.
        file: the image bytes content.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The asset description.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        storage, _ = configuration.storage, configuration.doc_db_asset

        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )

        if [img for img in asset["images"] if img.split("/")[-1] == filename]:
            raise HTTPException(
                status_code=409, detail=f"image '{filename}' already exist"
            )

        image = await format_image(filename, file)
        thumbnail = get_thumbnail(image, size=(200, 200))

        doc = {
            **asset,
            **{
                "images": [
                    *asset["images"],
                    f"/api/assets-backend/assets/{asset_id}/images/{image.name}",
                ],
                "thumbnails": [
                    *asset["thumbnails"],
                    f"/api/assets-backend/assets/{asset_id}/thumbnails/{thumbnail.name}",
                ],
            },
        }

        await db_post(doc=doc, configuration=configuration, context=ctx)

        post_image_body = FileData(
            objectData=image.content,
            objectName=Path(asset["kind"]) / asset_id / "images" / image.name,
            owner=Constants.public_owner,
            objectSize=len(image.content),
            content_type="image/" + image.extension,
            content_encoding="",
        )

        post_thumbnail_body = FileData(
            objectData=thumbnail.content,
            objectName=Path(asset["kind"]) / asset_id / "thumbnails" / thumbnail.name,
            owner=Constants.public_owner,
            objectSize=len(thumbnail.content),
            content_type="image/" + thumbnail.extension,
            content_encoding="",
        )

        post_file_bodies = [post_image_body, post_thumbnail_body]

        await asyncio.gather(
            *[
                storage.post_object(
                    path=post_file_body.objectName,
                    content=post_file_body.objectData,
                    owner=post_file_body.owner,
                    content_type=post_file_body.content_type,
                    headers=ctx.headers(),
                )
                for post_file_body in post_file_bodies
            ]
        )
        return await get_asset_implementation(
            request=request, asset_id=asset_id, configuration=configuration, context=ctx
        )


@router.delete(
    "/assets/{asset_id}/images/{filename}",
    response_model=AssetResponse,
    summary="remove an image",
)
async def remove_image(
    request: Request,
    asset_id: str,
    filename: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Removes an image of an asset. The associated thumbnail is also removed.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        filename: Name of the image.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The asset description.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        storage, _ = configuration.storage, configuration.doc_db_asset

        asset = await db_get(
            asset_id=asset_id, configuration=configuration, context=ctx
        )
        base_path = Path("/api/assets-backend/") / "assets" / asset_id
        doc = {
            **asset,
            **{
                "images": [
                    image
                    for image in asset["images"]
                    if image != str(base_path / "images" / filename)
                ],
                "thumbnails": [
                    thumbnail
                    for thumbnail in asset["thumbnails"]
                    if thumbnail != str(base_path / "thumbnails" / filename)
                ],
            },
        }
        await db_post(doc=doc, configuration=configuration, context=ctx)
        await asyncio.gather(
            storage.delete(
                Path(asset["kind"]) / asset_id / "images" / filename,
                owner=Constants.public_owner,
                headers=ctx.headers(),
            ),
            storage.delete(
                Path(asset["kind"]) / asset_id / "thumbnails" / filename,
                owner=Constants.public_owner,
                headers=ctx.headers(),
            ),
        )
        return await get_asset_implementation(
            request=request, asset_id=asset_id, configuration=configuration, context=ctx
        )


async def get_media(
    asset_id: str,
    name: str,
    media_type: str,
    configuration: Configuration,
    context: Context,
):
    asset = await db_get(
        asset_id=asset_id, configuration=configuration, context=context
    )

    storage = configuration.storage
    path = Path(asset["kind"]) / asset_id / media_type / name
    file = await storage.get_bytes(
        path, owner=Constants.public_owner, headers=context.headers()
    )
    return Response(
        content=file,
        headers={
            "Content-Encoding": "",
            "Content-Type": f"image/{path.suffix[1:]}",
            "cache-control": "public, max-age=31536000",
        },
    )


@router.get(
    "/assets/{asset_id}/images/{name}",
    summary="Retrieves a persisted image of an asset.",
)
async def get_media_image(
    request: Request,
    asset_id: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> Response:
    """
    Retrieves a persisted image of an asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        name: Name of the image.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The image.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await get_media(
            asset_id=asset_id,
            name=name,
            media_type="images",
            configuration=configuration,
            context=ctx,
        )


@router.get(
    "/assets/{asset_id}/thumbnails/{name}",
    summary="Retrieves the thumbnail of a persisted image of an asset.",
)
async def get_media_thumbnail(
    request: Request,
    asset_id: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Retrieves the thumbnail of a persisted image of an asset.

    Parameters:
        request: Incoming request.
        asset_id: Asset's ID.
        name: Name of the image.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.assets.configurations.Configuration).

    Return:
        The image.
    """
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await get_media(
            asset_id=asset_id,
            name=name,
            media_type="images",
            configuration=configuration,
            context=ctx,
        )
