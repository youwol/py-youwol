# third parties
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request


class VaryHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        key_header = "vary"
        values_header = (
            "Origin, Access-Control-Request-Headers, Access-Control-Request-Method"
        )
        if key_header in response.headers.keys():
            values_header = f"{response.headers.get(key_header)}, {values_header}"
        response.headers[key_header] = values_header
        return response
