# standard library
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# typing
from typing import Any, Generic, Type, TypeVar

# third parties
from aiohttp import ClientResponse
from pydantic import BaseModel

# Youwol clients
from yw_clients.common.json_utils import JSON

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
