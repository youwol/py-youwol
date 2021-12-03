from asset_auto_download import encode_id
from configuration.youwol_configuration import yw_config
from aiohttp import ClientConnectorError, ClientSession
from errors import HTTPResponseException


from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class LiveServingCdnMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp,
                 ) -> None:
        super().__init__(app)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        if request.method != "GET" or not request.url.path.startswith("/api/cdn-backend/resources/"):
            return await call_next(request)

        try:
            config = await yw_config()
        except HTTPResponseException as e:
            return e.httpResponse

        live_servers = config.userConfig.cdn.liveServers
        matching_urls = [(package_name, f"/api/cdn-backend/resources/{encode_id(package_name)}", port)
                         for package_name, port in live_servers.items()]
        match = next(((package_name, url, port) for package_name, url, port in matching_urls
                      if request.url.path.startswith(url)), None)

        if match:
            package_name, url, port = match
            rest_of_path = request.url.path.split('/')[-1]
            url = f"http://localhost:{port}/{rest_of_path}"
            try:
                # Try to connect to a dev server
                async with ClientSession(auto_decompress=False) as session:
                    async with await session.get(url=url) as resp:
                        content = await resp.read()
                        return Response(content=content, headers={k: v for k, v in resp.headers.items()})
            except ClientConnectorError:
                pass

        return await call_next(request)
