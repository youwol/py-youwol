# standard library
import json

from urllib.error import URLError
from urllib.request import urlopen

# typing
from typing import Any, Dict, List, Optional, TypeVar

# third parties
from aiohttp import ClientResponse, ClientSession, FormData, TCPConnector
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.exceptions import upstream_exception_from_response


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
        if response.status >= 400:
            raise await upstream_exception_from_response(response)
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

        raise ValueError(f"Unexpected method {incoming_request.method}")


async def aiohttp_to_starlette_response(resp: ClientResponse) -> Response:
    if resp.status < 300:
        return Response(
            status_code=resp.status,
            content=await resp.read(),
            headers=dict(resp.headers.items()),
        )
    raise await upstream_exception_from_response(resp, url=resp.url)


TResp = TypeVar("TResp")


def extract_bytes_ranges(request: Request) -> Optional[list[tuple[int, int]]]:
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


def aiohttp_file_form(
    filename: str, content_type: str, content: Any, file_id: Optional[str] = None
) -> FormData:
    """
    Create a `FormData` to upload a file (e.g. using
    [assets_gateway](@yw-nav-func:youwol.backends.assets_gateway.routers.assets.upload))

    Parameters:
        filename: Name of the file.
        content_type: Content type of the file, see []().
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


class FuturesResponse(Response):
    """
    This HTTP response is used when asynchronous computations (resolving after the HTTP response is returned)
    are needed.

    Example:
        ```python
        @app.get("/async-job")
        async def async_job(
            request: Request,
            task_id: int = Query(alias="task-id", default=int(time.time() * 1e6)),
        ):
            async def tick_every_second(streamer: FuturesResponse, context: BackendContext):
                async with context.start(action="tick_every_second") as ctx_ticks:
                    for i in range(1, 11):
                        await streamer.next(Data(content=f"Second {i}"), context=ctx_ticks)
                        await asyncio.sleep(1)
                    await streamer.close(context=ctx_ticks)

            async with init_context(request).start(action="/async-job") as ctx:
                response = FuturesResponse(channel_id=str(task_id))
                await ctx.info("Use web socket to send async. messages")
                asyncio.ensure_future(tick_every_second(response, ctx))
                return response
        ```
    """

    media_type = "application/json"

    def __init__(
        self,
        channel_id: str,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
    ) -> None:
        super().__init__(
            content={"channelId": channel_id},
            status_code=202,
            headers=headers,
            media_type=media_type,
        )
        self.channel_id = channel_id

    async def next(
        self, content: BaseModel, context: Context, labels: Optional[List[str]] = None
    ):
        await context.send(
            data=content,
            labels=[*context.with_labels, *(labels or []), self.channel_id],
        )

    async def close(self, context: Context):
        class FuturesResponseEnd(BaseModel):
            pass

        await context.send(
            data=FuturesResponseEnd(),
            labels=[self.channel_id],
        )

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
