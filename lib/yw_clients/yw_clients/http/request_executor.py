# standard library
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# typing
from typing import Any, Generic, Type, TypeVar

# third parties
from aiohttp import ClientResponse, ClientSession
from pydantic import BaseModel

# Youwol clients
from yw_clients.common.json_utils import JSON
from yw_clients.http.exceptions import upstream_exception_from_response

ClientResponseT = TypeVar("ClientResponseT", ClientResponse, Any)
"""
Type var definition for a response of a request,
used as template parameter of :class:`RequestExecutor <yw_clients.http.request_executor.RequestExecutor>`.

E.g. in case of aiohttp executor, it is
[ClientResponse](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientResponse).
"""

ParsedResponseT = TypeVar("ParsedResponseT")
BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class EmptyResponse(BaseModel):
    """
    Empty response.
    """


@dataclass(frozen=True)
class FileResponse(ABC, Generic[ClientResponseT]):

    resp: ClientResponseT

    @abstractmethod
    async def read(self) -> bytes:
        """
        Return:
            Bytes content.
        """

    @abstractmethod
    async def json(self, **kwargs) -> JSON:
        """
        Return:
            Content parsed in JSON.
        """

    @abstractmethod
    async def text(self, **kwargs) -> str:
        """
        Return:
            Content parsed in string.
        """


class RequestExecutor(ABC, Generic[ClientResponseT]):
    """
    Abstract class for requests executor.

    It has a class template type `Generic[TClientResponse]`.
    """

    @abstractmethod
    async def get(
        self,
        url: str,
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        Execute a `GET` request.

        Parameters:
            url: URL of the request.
            reader: the reader used to parse the response.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def post(
        self,
        url: str,
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        Execute a `POST` request.

        Parameters:
            url: URL of the request.
            reader: the reader used to parse the response.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def put(
        self,
        url: str,
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        Execute a `PUT` request.

        Parameters:
            url: URL of the request.
            reader: the reader used to parse the response.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def delete(
        self,
        url: str,
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> ParsedResponseT:
        """
        Execute a `DELETE` request.

        Parameters:
            url: URL of the request.
            reader: the reader used to parse the response.
            headers: headers to use with the request

        Return:
            The type of the response depends on the `default_reader` or `̀custom_reader` if provided.
        """

    @abstractmethod
    async def json_reader(self, resp: ClientResponseT, **kwargs) -> JSON:
        """Client response to JSON."""

    @abstractmethod
    async def text_reader(self, resp: ClientResponseT, **kwargs) -> str:
        """Client response to string."""

    @abstractmethod
    async def bytes_reader(self, resp: ClientResponseT, **kwargs) -> bytes:
        """Client response to bytes."""

    @abstractmethod
    async def file_reader(self, resp: ClientResponseT, **kwargs) -> FileResponse:
        """Client response to file."""

    @abstractmethod
    def typed_reader(
        self,
        target: Type[BaseModelT],
    ) -> Callable[[ClientResponseT], Awaitable[BaseModelT]]:
        """
        Return the response as expected pydantic's BaseModel.

        Parameters:
            target: The type expected.
        Return:
            The reader function.
        """


class AioHttpFileResponse(FileResponse[ClientResponse]):

    async def read(self) -> bytes:
        return await self.resp.read()

    async def json(self, **kwargs) -> JSON:
        return await self.resp.json(**kwargs)

    async def text(self, **kwargs) -> str:
        return await self.resp.text(**kwargs)


@dataclass(frozen=True)
class AioHttpExecutor(RequestExecutor[ClientResponse]):
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
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
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
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
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
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
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
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
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
        reader: Callable[[ClientResponseT], Awaitable[ParsedResponseT]],
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
            resp_json = await resp.json()
            return resp_json

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def text_reader(self, resp: ClientResponse, **kwargs) -> str:
        if resp.status < 300:
            resp_text = await resp.text()
            return resp_text

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def bytes_reader(self, resp: ClientResponse, **kwargs) -> bytes:
        if resp.status < 300:
            resp_bytes = await resp.read()
            return resp_bytes

        raise await upstream_exception_from_response(resp, url=resp.url)

    async def file_reader(self, resp: ClientResponse, **kwargs) -> AioHttpFileResponse:
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

        async def reader(resp: ClientResponseT) -> BaseModelT:
            if resp.status < 300:
                resp_json = await self.json_reader(resp)
                if not isinstance(resp_json, dict):
                    raise ValueError("The response recieved is not a valid dict")
                return target(**resp_json)

            raise await upstream_exception_from_response(resp, url=resp.url)

        return reader
