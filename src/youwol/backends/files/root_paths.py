# standard library
import io
import itertools
import uuid

# third parties
from fastapi import APIRouter, Depends
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

# Youwol utilities
from youwol.utils import AnyDict, get_content_encoding, get_content_type
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


@router.post("/files", response_model=PostFileResponse, summary="Upload a file.")
async def upload(
    request: Request, configuration: Configuration = Depends(get_configuration)
) -> PostFileResponse:
    """
    Upload a file.

    Example:
        To upload a file using aioHttp & the file client
        ```python
        from aiohttp import FormData
        from youwol.app import YouwolEnvironment


        form_data = FormData()
        form_data.add_field(
            name="file",
            value="the content of the file",
            filename="the-file-name.txt",
            content_type="text/plain",
        )

        form_data.add_field("content_type", "text/plain")
        form_data.add_field("content_encoding", "Identity")
        # optional: form_data.add_field("file_id", "a-unique-file-id")
        form_data.add_field("file_name", "the-file-name.txt")

        # within youwol module, a `ctx: Context` object should be available:
        resp = await LocalClients
        .get_files_client(env=await ctx.get('env', YouwolEnvironment))
        .upload(
            data=form_data,
            params={"folder-id": folder_id},
            headers=ctx.headers()
        )
        # outside youwol module, a `request: Request` object should be available:
        resp2 = AssetsGatewayClient(
            url_base="http://localhost:2000/api/assets-gateway",
            request_executor=AioHttpExecutor()
        )
        .get_files_backend_router()
        .upload(
            data=form_data,
            params={"folder-id": folder_id},
            cookies=request.cookies
        )
        ```

    Parameters:
        request: Incoming request. It should be associated with a form having the attributes:
            *  `file`: The content of the file as bytes.
            *  `file_id`: Optional, a provided file's ID (if not provided generate a `uuid`)
            *  `file_name`: The name of the file.
            *  `content_type`: Optional, the content type.
            If not provided it is guessed from the extension of the name (see
            [get_content_type](@yw-nav-func:youwol.utils.utils.get_content_type)).
            *  `content_encoding`: Optional, the content encoding.
            If not provided it is guessed from the extension of the name (see
            [get_content_encoding](@yw-nav-func:youwol.utils.utils.get_content_encoding)).
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration).

    Return:
        File information
    """
    async with Context.start_ep(request=request):
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ValueError("Field `file` of form is not of type `UploadFile`")
        file_id = form.get("file_id", None) or str(uuid.uuid4())
        if not isinstance(file_id, str):
            raise ValueError("Field `file_id` of form is not of type `str`")
        filename = form.get("file_name", "default_name")
        if not isinstance(filename, str):
            raise ValueError("Field `filename` of form is not of type `str`")
        content = await file.read()
        content_type = form.get("content_type", file.content_type) or get_content_type(
            filename
        )
        if not isinstance(content_type, str):
            raise ValueError("Field `content_type` of form is not of type `str`")
        content_encoding = form.get("content_encoding", "") or get_content_encoding(
            filename
        )
        if not isinstance(content_encoding, str):
            raise ValueError("Field `content_encoding` of form is not of type `str`")
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
    summary="Retrieve file's metadata.",
)
async def get_info(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Retrieve file's metadata.

    Parameters:
        request: Incoming request.
        file_id: File's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration).

    Return:
        The file's metadata.
    """
    async with Context.start_ep(request=request):
        return await configuration.file_system.get_info(object_id=file_id)


@router.post("/files/{file_id}/metadata", summary="update metadata")
async def update_metadata(
    request: Request,
    file_id: str,
    body: PostMetadataBody,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Update file's metadata.

    Parameters:
        request: Incoming request.
        file_id: File's ID.
        body: metadata description.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration).

    Return:
        Empty JSON.
    """
    async with Context.start_ep(request=request):
        await configuration.file_system.set_metadata(
            object_id=file_id, metadata=Metadata(**body.dict())
        )
        return {}


@router.get("/files/{file_id}", summary="Retrieve file's content.")
async def get_file(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> Response:
    """
    Retrieve file's content.

    Parameters:
        request: Incoming request.
        file_id: File's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration).

    Return:
        The file's content.
    """
    async with Context.start_ep(
        request=request, with_attributes={"fileId": file_id}
    ) as ctx:
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


@router.delete("/files/{file_id}", summary="Remove a file.")
async def remove_file(
    request: Request,
    file_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Remove a file.

    Parameters:
        request: Incoming request.
        file_id: File's ID.
        configuration: Injected [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration).

    Return:
        Empty JSON.
    """
    async with Context.start_ep(request=request):
        await configuration.file_system.remove_object(object_id=file_id)
        return {}
