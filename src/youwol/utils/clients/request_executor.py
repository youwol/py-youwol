# standard library
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Any, Callable, Generic, Optional, TypeVar, Union

# third parties
from aiohttp import ClientResponse, ClientSession

# Youwol utilities
from youwol.utils.exceptions import upstream_exception_from_response
from youwol.utils.types import JSON

TClientResponse = TypeVar("TClientResponse")
"""
Type var definition for a response of a request,
used as template parameter of [RequestExecutor](@yw-nav-class:youwol.utils.clients.request_executor.RequestExecutor).

E.g. in case of aiohttp executor, it is
[ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse).
"""


class RequestExecutor(ABC, Generic[TClientResponse]):
    """
    Abstract class for requests executor.

    It has a class template type `Generic[TClientResponse]`.
    """

    @abstractmethod
    async def get(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[TClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        Execute a `GET` request.

        Parameters:
            url: URL of the request.
            default_reader: the default reader to parse the response.
            custom_reader: if provided, this custom reader is used in place of the `default_reader`.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def post(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[TClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        Execute a `POST` request.

        Parameters:
            url: URL of the request.
            default_reader: the default reader to parse the response.
            custom_reader: if provided, this custom reader is used in place of the `default_reader`.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def put(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[TClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        Execute a `PUT` request.

        Parameters:
            url: URL of the request.
            default_reader: the default reader to parse the response.
            custom_reader: if provided, this custom reader is used in place of the `default_reader`.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def delete(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[TClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        Execute a `DELETE` request.

        Parameters:
            url: URL of the request.
            default_reader: the default reader to parse the response.
            custom_reader: if provided, this custom reader is used in place of the `default_reader`.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """


@dataclass(frozen=True)
class AioHttpExecutor(RequestExecutor[ClientResponse]):
    """
    Request executor using [AioHTTP](https://docs.aiohttp.org/en/stable/) instantiated using the template parameter
    [ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse)..

    Helpers regarding readers are available, see
    [text_reader](@yw-nav-func:youwol.utils.clients.request_executor.text_reader),
    [json_reader](@yw-nav-func:youwol.utils.clients.request_executor.json_reader),
    [bytes_reader](@yw-nav-func:youwol.utils.clients.request_executor.bytes_reader),
    [auto_reader](@yw-nav-func:youwol.utils.clients.request_executor.auto_reader).
    """

    client_session: Union[ClientSession, Callable[[], ClientSession]] = (
        lambda: ClientSession(auto_decompress=False)
    )
    """
    Client session from [AioHTTP](https://docs.aiohttp.org/en/stable/).

    If an instance is provided, it is used as it is to send requests.

    If a callable is provided, the callable is triggered each time a request is send to retrieve a new client session.
    """
    access_token: Optional[Callable[[], Awaitable[str]]] = None

    @staticmethod
    def _get_session():
        return ClientSession(auto_decompress=False)

    async def _trigger_request(
        self, request: Callable[[ClientSession], Awaitable[Any]]
    ):
        if isinstance(self.client_session, ClientSession):
            return await request(self.client_session)

        async with self.client_session() as session:
            return await request(session)

    async def _resolve_headers(self, headers: Optional[dict[str, str]]):
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
        default_reader: Callable[[ClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[ClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        resolved_headers = await self._resolve_headers(headers)
        kwargs.pop("headers", None)
        reader = custom_reader or default_reader

        async def request(session: ClientSession):
            async with await session.request(
                method=method, url=url, headers=resolved_headers, **kwargs
            ) as resp:
                return await reader(resp)

        return await self._trigger_request(request=request)

    async def get(
        self,
        url: str,
        default_reader: Callable[[ClientResponse], Awaitable[Any]],
        custom_reader: Optional[Callable[[ClientResponse], Awaitable[Any]]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        See [RequestExecutor.post](@yw-nav-func:youwol.utils.clients.request_executor.RequestExecutor.get).
        """
        return await self._request(
            "GET",
            url=url,
            default_reader=default_reader,
            custom_reader=custom_reader,
            headers=headers,
            **kwargs,
        )

    async def post(
        self,
        url: str,
        default_reader: Callable[[ClientResponse], Any],
        custom_reader: Optional[Callable[[ClientResponse], Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        See [RequestExecutor.post](@yw-nav-func:youwol.utils.clients.request_executor.RequestExecutor.post).
        """
        return await self._request(
            "POST",
            url=url,
            default_reader=default_reader,
            custom_reader=custom_reader,
            headers=headers,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        default_reader: Callable[[ClientResponse], Any],
        custom_reader: Optional[Callable[[ClientResponse], Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        See [RequestExecutor.put](@yw-nav-func:youwol.utils.clients.request_executor.RequestExecutor.put).
        """
        return await self._request(
            "PUT",
            url=url,
            default_reader=default_reader,
            custom_reader=custom_reader,
            headers=headers,
            **kwargs,
        )

    async def delete(
        self,
        url: str,
        default_reader: Callable[[ClientResponse], Any],
        custom_reader: Optional[Callable[[ClientResponse], Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ):
        """
        See [RequestExecutor.delete](@yw-nav-func:youwol.utils.clients.request_executor.RequestExecutor.delete).
        """
        return await self._request(
            "DELETE",
            url=url,
            default_reader=default_reader,
            custom_reader=custom_reader,
            headers=headers,
            **kwargs,
        )


async def text_reader(resp: ClientResponse) -> str:
    """
    Text reader from aiohttp's
    [ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse).

    Parameters:
        resp: The response.

    Return:
        The content as string.
    """
    if resp.status < 300:
        resp_text = await resp.text()
        return resp_text

    raise await upstream_exception_from_response(resp, url=resp.url)


async def json_reader(resp: ClientResponse) -> JSON:
    """
    JSON reader from aiohttp's
    [ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse).

    Parameters:
        resp: The response.

    Return:
        The content as JSON.
    """
    if resp.status < 300:
        resp_json = await resp.json()
        return resp_json

    raise await upstream_exception_from_response(resp, url=resp.url)


async def bytes_reader(resp: ClientResponse) -> bytes:
    """
    Bytes reader from aiohttp's
    [ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse).

    Parameters:
        resp: The response.

    Return:
        The content as bytes.
    """
    if resp.status < 300:
        resp_bytes = await resp.read()
        return resp_bytes

    raise await upstream_exception_from_response(resp, url=resp.url)


async def auto_reader(resp: ClientResponse) -> Union[JSON, str, bytes]:
    """
    Automatic selection of reader from the response's `content_type`.
    See code implementation regarding switching strategy.

    Parameters:
        resp: The response.

    Return:
        The content as JSON, string or bytes (default).
    """
    if resp.status < 300:
        content_type = resp.content_type

        if content_type == "application/json":
            return await resp.json()

        text_applications = ["rtf", "xml", "x-sh"]
        if content_type.startswith("text/") or content_type in [
            f"application/{app}" for app in text_applications
        ]:
            return await resp.text()

        return await resp.read()

    raise await upstream_exception_from_response(resp)
