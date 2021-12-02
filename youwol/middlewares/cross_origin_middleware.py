from typing import List
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class CrossOriginMiddleware(BaseHTTPMiddleware):

    def __init__(self,
                 app: ASGIApp,
                 frontends_base_path: List[str]
                 ) -> None:
        super().__init__(app)
        self.fronts_base_path = frontends_base_path

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
            ) -> Response:

        resp = await call_next(request)
        if any([t in request.url.path for t in self.fronts_base_path]):
            resp.headers.update({'Cross-Origin-Opener-Policy': 'same-origin'})
            resp.headers.update({'Cross-Origin-Embedder-Policy': 'require-corp'})
        return resp
