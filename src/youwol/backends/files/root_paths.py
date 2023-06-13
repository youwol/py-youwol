# standard library
import io
import itertools
import uuid

# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

# Youwol utilities
from youwol.utils import get_content_encoding, get_content_type
from youwol.utils.clients.file_system.interfaces import Metadata
from youwol.utils.context import Context
from youwol.utils.http_clients.files_backend import (
    GetInfoResponse,
    PostFileResponse,
    PostMetadataBody,
)

# relative
from .configurations import Configuration, get_configuration

router = APIRouter(tags=["files-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "file-backend serving"}


@router.post("/files", response_model=PostFileResponse, summary="create a new file")
async def upload(
    request: Request, configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(request=request):  # type: Context
        form = await request.form()
        file = form.get("file")
        file_id = form.get("file_id", None) or str(uuid.uuid4())
        filename = form.get("file_name", "default_name")
        content = await file.read()
        content_type = form.get("content_type", file.content_type) or get_content_type(
            filename
        )
        content_encoding = form.get("content_encoding", "") or get_content_encoding(
            filename
        )
        await configuration.file_system.put_object(
            object_id=file_id,
            object_name=filename,
            data=io.BytesIO(content),
            content_type=content_type,
            content_encoding=content_encoding,
        )

        resp = PostFileResponse(
            fileId=file_id,
            fileName=filename,
            contentType=content_type,
            contentEncoding=content_encoding,
        )

        return resp


@router.get(
    "/files/{file_id}/info",
    response_model=GetInfoResponse,
    summary="get file stats information",
)
async def get_info(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request):  # type: Context
        return await configuration.file_system.get_info(object_id=file_id)


@router.post("/files/{file_id}/metadata", summary="update metadata")
async def update_metadata(
    request: Request,
    file_id: str,
    body: PostMetadataBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request):  # type: Context
        await configuration.file_system.set_metadata(
            object_id=file_id, metadata=Metadata(**body.dict())
        )
        return {}


@router.get("/files/{file_id}", summary="get file content")
async def get_file(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"fileId": file_id}
    ) as ctx:  # type: Context
        stats = await configuration.file_system.get_info(object_id=file_id)
        content = await configuration.file_system.get_object(object_id=file_id)
        max_age = "31536000"
        await ctx.info("Retrieved file", data={"stats": stats, "size": len(content)})
        return Response(
            content=content,
            headers={
                "Content-Encoding": stats["metadata"]["contentEncoding"],
                "Content-Type": stats["metadata"]["contentType"],
                "cache-control": f"public, max-age={max_age}",
                "content-length": f"{len(content)}",
            },
        )


@router.delete("/files/{file_id}", summary="remove a file")
async def remove_file(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request):  # type: Context
        await configuration.file_system.remove_object(object_id=file_id)
        return {}
