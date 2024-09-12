# typing
from typing import Any

# third parties
from aiohttp import ClientResponse, FormData
from starlette.responses import Response

# Youwol clients
from yw_clients.http.exceptions import upstream_exception_from_response


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
