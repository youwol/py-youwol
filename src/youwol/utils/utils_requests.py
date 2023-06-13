# standard library
from urllib.error import URLError
from urllib.request import urlopen

# typing
from typing import Awaitable, Callable, List, Optional, Tuple, TypeVar, Union

# third parties
from aiohttp import ClientResponse, ClientSession, TCPConnector
from starlette.requests import Request
from starlette.responses import Response

# Youwol utilities
from youwol.utils.exceptions import assert_response
from youwol.utils.types import JSON


async def redirect_request(
    incoming_request: Request,
    origin_base_path: str,
    destination_base_path: str,
    headers=None,
) -> Response:
    rest_of_path = incoming_request.url.path.split(origin_base_path)[1].strip("/")
    headers = dict(incoming_request.headers.items()) if not headers else headers
    redirect_url = f"{destination_base_path}/{rest_of_path}"

    async def forward_response(response):
        await assert_response(response)
        headers_resp = dict(response.headers.items())
        content = await response.read()
        return Response(
            status_code=response.status, content=content, headers=headers_resp
        )

    params = incoming_request.query_params
    # after this eventual call, a subsequent call to 'body()' will hang forever
    data = (
        await incoming_request.body()
        if incoming_request.method in ["POST", "PUT", "DELETE"]
        else None
    )

    async with ClientSession(
        connector=TCPConnector(verify_ssl=False), auto_decompress=False
    ) as session:
        if incoming_request.method == "GET":
            async with await session.get(
                url=redirect_url, params=params, headers=headers
            ) as resp:
                return await forward_response(resp)

        if incoming_request.method == "POST":
            async with await session.post(
                url=redirect_url, data=data, params=params, headers=headers
            ) as resp:
                return await forward_response(resp)

        if incoming_request.method == "PUT":
            async with await session.put(
                url=redirect_url, data=data, params=params, headers=headers
            ) as resp:
                return await forward_response(resp)

        if incoming_request.method == "DELETE":
            async with await session.delete(
                url=redirect_url, data=data, params=params, headers=headers
            ) as resp:
                return await forward_response(resp)


async def aiohttp_to_starlette_response(resp: ClientResponse) -> Response:
    return Response(
        status_code=resp.status,
        content=await resp.read(),
        headers=dict(resp.headers.items()),
    )


TResp = TypeVar("TResp")


async def extract_aiohttp_response(
    resp: ClientResponse, reader: Callable[[ClientResponse], Awaitable[TResp]] = None
) -> Union[TResp, JSON, str, bytes]:
    if reader:
        return await reader(resp)
    content_type = resp.content_type

    if content_type == "application/json":
        return await resp.json()

    text_applications = ["rtf", "xml", "x-sh"]
    if content_type.startswith("text/") or content_type in [
        f"application/{app}" for app in text_applications
    ]:
        return await resp.text()

    return await resp.read()


def extract_bytes_ranges(request: Request) -> Optional[List[Tuple[int, int]]]:
    range_header = request.headers.get("range")
    if not range_header:
        return None

    ranges_str = range_header.split("=")[1].split(",")

    def to_range_number(range_str: str):
        elems = range_str.split("-")
        return int(elems[0]), int(elems[1])

    return [to_range_number(r) for r in ranges_str]


def is_server_http_alive(url: str):
    try:
        with urlopen(url):
            return True
    except URLError:
        return False
