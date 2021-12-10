from typing import Tuple

from auto_download.auto_download_thread import encode_id
from aiohttp import ClientConnectorError, ClientSession

from context import Context

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .common import DispatchingRule


class LiveServingCdnDispatch(DispatchingRule):

    match: Tuple[str, str, int] = None

    async def is_matching(self, request: Request, context: Context) -> bool:
        if request.method != "GET":
            return False
        # When serving a package through live server we intercept 2 routes:
        # - in any case the 'low-level' call to cdn-backend is intercepted
        # - the higher level call through assets-gateway is also intercepted such that permission call is skipped
        # (the package may not be published yet)
        if not(request.url.path.startswith("/api/assets-gateway/raw/package") or
               request.url.path.startswith("/api/cdn-backend/resources/")):
            return False

        live_servers = context.config.userConfig.cdn.liveServers
        matching_urls = [(package_name, f"/api/assets-gateway/raw/package/{encode_id(package_name)}", port)
                         for package_name, port in live_servers.items()] + \
                        [(package_name, f"/api/cdn-backend/resources/{encode_id(package_name)}", port)
                         for package_name, port in live_servers.items()]
        self.match = next(((package_name, url, port) for package_name, url, port in matching_urls
                           if request.url.path.startswith(url)), None)

        return self.match is not None

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        package_name, url, port = self.match
        rest_of_path = request.url.path.split('/')[-1]
        url = f"http://localhost:{port}/{rest_of_path}"
        try:
            # Try to connect to a dev server
            async with ClientSession(auto_decompress=False) as session:
                async with await session.get(url=url) as resp:
                    content = await resp.read()
                    return Response(content=content, headers={k: v for k, v in resp.headers.items()})
        except ClientConnectorError:
            return await call_next(request)
