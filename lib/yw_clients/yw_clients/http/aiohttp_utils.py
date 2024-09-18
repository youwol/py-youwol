# standard library
from collections.abc import Callable
from dataclasses import dataclass

# typing
from typing import Any, Awaitable, Type, TypeVar

# third parties
from aiohttp import ClientResponse, ClientSession, FormData
from pydantic import BaseModel
from starlette.responses import Response

# Youwol clients
from yw_clients.common.json_utils import JSON
from yw_clients.http.exceptions import upstream_exception_from_response


ParsedResponseT = TypeVar("ParsedResponseT")
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class EmptyResponse(BaseModel):
    """
    Empty response.
    """



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


@dataclass(frozen=True)
class AioHttpFileResponse:
    resp: ClientResponse

    async def read(self) -> bytes:
        return await self.resp.read()

    async def json(self, **kwargs) -> JSON:
        return await self.resp.json(**kwargs)

    async def text(self, **kwargs) -> str:
        return await self.resp.text(**kwargs)


@dataclass(frozen=True)
class AioHttpExecutor:
    """
    Request executor using [AioHTTP](https://docs.aiohttp.org/en/stable/) instantiated using the template parameter
    [ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse)..

    Helpers regarding readers are available, see
    :func:`text_reader <yw_clients.http.request_executor.text_reader>`,
    :func:`json_reader <yw_clients.http.request_executor.json_reader>`,
    :func:`bytes_reader <yw_clients.http.request_executor.bytes_reader>`,
    :func:`auto_reader <yw_clients.http.request_executor.auto_reader>`.
    """

    client_session: ClientSession | Callable[[], ClientSession] = lambda: ClientSession(
        auto_decompress=False
    )
    """
    Client session from [AioHTTP](https://docs.aiohttp.org/en/stable/).

    If an instance is provided, it is used as it is to send requests.

    If a callable is provided, the callable is triggered each time a request is send to retrieve a new client session.
    """
    access_token: Callable[[], Awaitable[str]] | None = None

    @staticmethod
    def _get_session():
        return ClientSession(auto_decompress=False)

    async def _trigger_request(
        self, request: Callable[[ClientSession], Awaitable[ParsedResponseT]]
    ):
        if isinstance(self.client_session, ClientSession):
            return await request(self.client_session)

        async with self.client_session() as session:
            return await request(session)

    async def _resolve_headers(self, headers: dict[str, str] | None):
        static_headers = headers or {}
        access_token = await self.access_token() if self.access_token else None
        dynamic_headers = (
            {"authorization": f"Bearer {access_token}"} if access_token else {}
        )
        return {**static_headers, **dynamic_headers}

    async def _request(
        self,
        method: str,
        url: str,
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        resolved_headers = await self._resolve_headers(headers)
        kwargs.pop("headers", None)

        async def request(session: ClientSession):
            async with await session.request(
                method=method, url=url, headers=resolved_headers, **kwargs
            ) as resp:
                return await reader(resp)

        return await self._trigger_request(request=request)

    async def get(
        self,
        url: str,
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        See :func:`RequestExecutor.post <yw_clients.http.request_executor.RequestExecutor.get>`.
        """
        return await self._request(
            "GET",
            url=url,
            reader=reader,
            headers=headers,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        See :func:`RequestExecutor.post <yw_clients.http.request_executor.RequestExecutor.post>`.
        """
        return await self._request(
            "POST",
            url=url,
            reader=reader,
            headers=headers,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        See :func:`RequestExecutor.put <yw_clients.http.request_executor.RequestExecutor.put>`.
        """
        return await self._request(
            "PUT",
            url=url,
            reader=reader,
            headers=headers,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        reader: Callable[[ClientResponse], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        See :func:`RequestExecutor.delete <yw_clients.http.request_executor.RequestExecutor.delete>`.
        """
        return await self._request(
            "DELETE",
            url=url,
            reader=reader,
            headers=headers,
            **kwargs,
        )

    async def json_reader(self, resp: ClientResponse, **kwargs) -> JSON:
        if resp.status < 300:
            resp_json = await resp.json(**kwargs)
            return resp_json

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def text_reader(self, resp: ClientResponse, **kwargs) -> str:
        if resp.status < 300:
            resp_text = await resp.text(**kwargs)
            return resp_text

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def bytes_reader(self, resp: ClientResponse) -> bytes:
        if resp.status < 300:
            resp_bytes = await resp.read()
            return resp_bytes

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def file_reader(self, resp: ClientResponse) -> AioHttpFileResponse:
        if resp.status < 300:
            return AioHttpFileResponse(resp=resp)

        raise await upstream_exception_from_response(resp)

    def typed_reader(
        self,
        target: Type[BaseModelT],
    ) -> Callable[[ClientResponse], Awaitable[BaseModelT]]:
        """
        Return the response as expected pydantic's BaseModel.

        Parameters:
            target: The type expected.
        Return:
            The reader function.
        """

        async def reader(resp: ClientResponse) -> BaseModelT:
            if resp.status < 300:
                resp_json = await self.json_reader(resp)
                if not isinstance(resp_json, dict):
                    raise ValueError("The response recieved is not a valid dict")
                return target(**resp_json)

            raise await upstream_exception_from_response(resp, url=resp.url)

        return reader


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
