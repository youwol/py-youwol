# typing
from typing import Annotated, Optional

# third parties
from aiohttp import ClientResponse
from fastapi.params import Header
from starlette.responses import Response, StreamingResponse

# relative
from ..constantes import PROXIED_HEADERS
from ..dependencies import Dependencies
from ..metrics import count_data_transferred, gauge_concurrent_streaming
from .models import ClientConfig, Origin

TypedHeader = Annotated[Optional[str], Header()]


async def client_response_to_streaming_response(
    resp: ClientResponse,
) -> StreamingResponse:
    async def _response_generator():
        gauge_concurrent_streaming.inc()
        async for chunk, _ in resp.content.iter_chunks():
            count_data_transferred.inc(len(chunk))
            yield chunk
        resp.close()
        gauge_concurrent_streaming.dec()

    return StreamingResponse(
        content=_response_generator(),
        status_code=resp.status,
        media_type=resp.content_type,
        headers={k: v for k, v in resp.headers.items() if k.lower() in PROXIED_HEADERS},
    )


def get_client_config(
    response: Response,
    if_none_match: str | None,
    deps: Dependencies,
) -> ClientConfig | None:
    etag = deps.configuration.version

    if if_none_match == str(etag):
        response.status_code = 304
        return None

    response.headers["etag"] = str(etag)
    response.headers["cache-control"] = "max-age=31536000, immutable"
    return ClientConfig(
        id=deps.configuration.config_id,
        origin=Origin.from_host(deps.configuration.host),
        pathLoadingGraph="/loading-graph",
        pathResource="/resource",
    )
