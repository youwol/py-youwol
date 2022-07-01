import urllib
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint, DispatchFunction
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette.types import ASGIApp

from youwol.environment.youwol_environment import yw_config
from youwol.routers.authorization import get_user_info
from youwol_utils.clients.oidc.oidc_config import OidcInfos
from youwol_utils.context import Context, Label
from youwol_utils.middlewares import JwtProvider


class AuthMiddleware(BaseHTTPMiddleware):
    cache = {}

    def __init__(self,
                 app: ASGIApp,
                 dispatch: DispatchFunction = None,
                 **_) -> None:
        super().__init__(app, dispatch)

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:

        config = await yw_config()

        async with Context.from_request(request).start(
                action=f"Authorisation middleware",
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:
            if not request.headers.get('authorization'):
                request.state.user_info = ''
                await ctx.info(text="No authorisation token found")
                # auth_token = await config.get_auth_token(context=ctx)
                # # A bit ugly, not very safe ... coming from:
                # # How to set request headers before path operation is executed
                # # https://github.com/tiangolo/fastapi/issues/2727
                # auth_header: Tuple[bytes, bytes] = "authorization".encode(), f"Bearer {auth_token}".encode()
                # request.headers.__dict__["_list"].append(auth_header)
            else:
                if not await self.authenticate(config.userEmail, request):
                    ctx.error(text="Unauthorized")
                    return Response(content="Unauthorized", status_code=403)

            #            await ctx.info(text="User info retrieved", data=request.state.user_info)
            return await call_next(request)

    async def authenticate(self, user_name: str, request: Request) -> bool:

        user_info = self.cache.get(user_name, None)
        if user_info:
            request.state.user_info = user_info
            return True

        user_info = await get_user_info(config=await yw_config())
        request.state.user_info = user_info
        self.cache[user_name] = user_info
        return True


class JwtProviderConfig(JwtProvider):

    async def get_token(self, request: Request, context: Context) -> Optional[str]:
        config = await yw_config()
        return await config.get_auth_token(context=context)


def redirect_on_missing_token(url):
    if url.path.startswith('/applications'):
        target_uri = urllib.parse.quote(str(url.path))
        login_flow = 'auto'
        if str(url.query).find('login_flow=temp') >= 0:
            login_flow = 'temp'
        if str(url.query).find('login_flow=user') >= 0:
            login_flow = 'user'
        return RedirectResponse(f"/api/accounts/openid_rp/login?target_uri={target_uri}&flow={login_flow}",
                                status_code=307)
    else:
        return Response(content="Unauthenticated", status_code=403),


async def get_remote_openid_infos() -> OidcInfos:
    config = await yw_config()
    return OidcInfos(base_uri=config.get_remote_info().openidBaseUrl, client=config.get_remote_info().openidClient)
