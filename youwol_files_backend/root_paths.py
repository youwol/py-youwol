import io
import itertools
import uuid

from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import Response

from youwol_files_backend import Configuration
from youwol_files_backend.configurations import get_configuration
from youwol_utils import get_content_type, get_content_encoding
from youwol_utils.context import Context
from youwol_utils.http_clients.files_backend import PostFileResponse, GetInfoResponse, PostMetadataBody

router = APIRouter(tags=["files-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "file-backend serving"}


@router.post(
    "/files",
    response_model=PostFileResponse,
    summary="create a new file"
)
async def upload(
        request: Request,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        form = await request.form()
        file = form.get('file')
        file_id = form.get('file_id', None) or str(uuid.uuid4())
        filename = form.get('file_name', "default_name")
        metadata = {
            "fileId": file_id,
            "fileName": filename,
            "contentType": form.get('content_type', file.content_type) or get_content_type(filename),
            "contentEncoding": form.get('content_encoding', '') or get_content_encoding(filename)
            }
        await ctx.info("File metadata", data=metadata)
        content = await file.read()
        await configuration.file_system.put_object(
            object_name=file_id,
            data=io.BytesIO(content),
            content_type=metadata["contentType"],
            metadata=metadata)

        resp = PostFileResponse(fileId=file_id, fileName=metadata['fileName'], contentType=metadata["contentType"],
                                contentEncoding=metadata["contentEncoding"])

        return resp


@router.get(
    "/files/{file_id}/info",
    response_model=GetInfoResponse,
    summary="get file stats information"
)
async def get_info(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ):  # type: Context
        return await configuration.file_system.get_info(object_name=file_id)


@router.post(
    "/files/{file_id}/metadata",
    summary="update metadata"
)
async def update_metadata(
        request: Request,
        file_id: str,
        body: PostMetadataBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ):  # type: Context
        actual_meta = (await configuration.file_system.get_info(object_name=file_id))['metadata']
        new_fields = {k: v for k, v in body.dict().items() if v}
        await configuration.file_system.set_metadata(object_name=file_id, metadata={**actual_meta, **new_fields})
        return {}


@router.get(
    "/files/{file_id}",
    summary="get file content"
)
async def get_file(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request,
            with_attributes={'fileId': file_id}
    ) as ctx:  # type: Context
        stats = await configuration.file_system.get_info(object_name=file_id)
        content = await configuration.file_system.get_object(object_name=file_id)
        max_age = "31536000"
        await ctx.info("Retrieved file", data={
            "stats": stats,
            "size": len(content)
        })
        return Response(
            content=content,
            headers={
                "Content-Encoding": stats['metadata']["contentEncoding"],
                "Content-Type": stats['metadata']["contentType"],
                "cache-control": f"public, max-age={max_age}",
                "content-length": f"{len(content)}"
            }
        )


@router.delete(
    "/files/{file_id}",
    summary="remove a file"
)
async def remove_file(
        request: Request,
        file_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ):  # type: Context
        await configuration.file_system.remove_object(object_name=file_id)
        return {}
