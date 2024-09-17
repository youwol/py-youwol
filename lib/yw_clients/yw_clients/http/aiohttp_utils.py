# typing
from typing import Any

# third parties
from aiohttp import ClientResponse, FormData
from starlette.responses import Response

# Youwol clients
from yw_clients.common.json_utils import JSON
from yw_clients.http.exceptions import upstream_exception_from_response
from yw_clients.http.request_executor import AioHttpFileResponse


async def aiohttp_to_starlette_response(resp: ClientResponse) -> Response:
    if resp.status < 300:
        return Response(
            status_code=resp.status,
            content=await resp.read(),
            headers=dict(resp.headers.items()),
        )
    raise await upstream_exception_from_response(resp, url=resp.url)


def aiohttp_file_form(
    filename: str, content_type: str, content: Any, file_id: str | None = None
) -> FormData:
    """
    Create a `FormData` to upload a file (e.g. using
    :func:`assets_gateway <youwol.backends.assets_gateway.routers.assets_backend.zip_all_files>`)

    Parameters:
        filename: Name of the file.
        content_type: Content type of the file.
        content: The actual content of the file.
        file_id: An explicit file's ID if provided (generated if not).

    Return:
        The form data.
    """
    form_data = FormData()
    form_data.add_field(
        name="file",
        value=content,
        filename=filename,
        content_type=content_type,
    )

    form_data.add_field("content_type", content_type)
    form_data.add_field("content_encoding", "Identity")
    form_data.add_field("file_id", file_id)
    form_data.add_field("file_name", filename)
    return form_data


async def parse_file_response(
    file_resp: AioHttpFileResponse,
) -> JSON | str | bytes:
    """
    Automatic selection of reader from the response's `content_type`.
    See code implementation regarding switching strategy.

    Parameters:
        file_resp: The response.

    Return:
        The content as JSON, string or bytes (default).
    """
    if file_resp.resp.status < 300:
        content_type = (
            file_resp.resp.content_type.lower() if file_resp.resp.content_type else ""
        )

        # Handle JSON response and variations of JSON content types
        if "application/json" in content_type or content_type.endswith("+json"):
            return await file_resp.json()

        # Handle common text-based responses and variations
        text_applications = ["rtf", "xml", "x-sh", "html", "javascript"]
        if content_type.startswith("text/") or any(
            app in content_type for app in text_applications
        ):
            return await file_resp.resp.text()

        # Handle other text-like content types with explicit charset
        if "charset" in content_type:
            return await file_resp.resp.text()

        # Handle any other unrecognized or binary content type
        return await file_resp.resp.read()

    raise await upstream_exception_from_response(file_resp.resp)
