# standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass

# typing
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar, Union

# third parties
from aiohttp import ClientResponse, ClientSession

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response
from youwol.utils.types import JSON

TClientResponse = TypeVar("TClientResponse")


class RequestExecutor(ABC, Generic[TClientResponse]):
    @abstractmethod
    async def get(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Callable[[TClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        pass

    @abstractmethod
    async def post(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Callable[[TClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        pass

    @abstractmethod
    async def put(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Callable[[TClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        pass

    @abstractmethod
    async def delete(
        self,
        url: str,
        default_reader: Callable[[TClientResponse], Awaitable[Any]],
        custom_reader: Callable[[TClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        pass


@dataclass(frozen=True)
class AioHttpExecutor(RequestExecutor[ClientResponse]):
    client_session: Union[ClientSession, Callable[[], ClientSession]]
    access_token: Callable[[], Awaitable[str]] = None

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

    async def _resolve_headers(self, headers: Optional[Dict[str, str]]):
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
        custom_reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
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
        custom_reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
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
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
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
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
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
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ):
        return await self._request(
            "DELETE",
            url=url,
            default_reader=default_reader,
            custom_reader=custom_reader,
            headers=headers,
            **kwargs,
        )


async def text_reader(resp: ClientResponse) -> str:
    if resp.status < 300:
        resp_text = await resp.text()
        return resp_text

    await raise_exception_from_response(resp, url=resp.url)


async def json_reader(resp: ClientResponse) -> JSON:
    if resp.status < 300:
        resp_json = await resp.json()
        return resp_json

    await raise_exception_from_response(resp, url=resp.url)


async def bytes_reader(resp: ClientResponse) -> bytes:
    if resp.status < 300:
        resp_bytes = await resp.read()
        return resp_bytes

    await raise_exception_from_response(resp, url=resp.url)
