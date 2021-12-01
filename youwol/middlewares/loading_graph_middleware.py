import json

import aiohttp
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import youwol.services.backs.cdn.root_paths as cdn
from youwol.services.backs.cdn.configurations import get_configuration
from services.backs.cdn.models import LoadingGraphBody
from youwol_utils import PackagesNotFound


class LoadingGraphMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp
                 ) -> None:
        super().__init__(app)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        if '/api/assets-gateway/cdn/queries/loading-graph' not in request.url.path:
            return await call_next(request)

        # <!> Be careful: a body can only be fetched one time, second call will hang forever <!>
        body_raw = await request.body()

        body = LoadingGraphBody(**(json.loads(body_raw.decode('utf8'))))
        config = await get_configuration()
        try:
            resp = await cdn.resolve_loading_tree(request, body, config)
            return Response(status_code=200, content=json.dumps(resp.dict()).encode('utf-8'))
        except PackagesNotFound:
            url = f'https://gc.platform.youwol.com{request.url.path}'
            headers = {"Authorization": request.headers.get("authorization")}
            async with aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(verify_ssl=False),
                    auto_decompress=False) as session:
                async with await session.post(url=url, json=body.dict(), headers=headers) as resp:
                    headers_resp = {k: v for k, v in resp.headers.items()}
                    content = await resp.read()
                    return Response(status_code=resp.status, content=content, headers=headers_resp)
