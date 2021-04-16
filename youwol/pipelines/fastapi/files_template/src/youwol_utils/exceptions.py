from aiohttp import ClientResponse
from fastapi import HTTPException


class YouWolException(HTTPException):
    def __init__(self, status_code: int, detail: str, **kwargs):
        self.status_code = status_code
        self.detail = detail
        self.parameters = kwargs


async def raise_exception_from_response(raw_resp: ClientResponse, **kwargs):

    detail = None

    try:
        resp = await raw_resp.json()
        if resp:
            detail = resp.get("detail", None) or resp.get("message", None) or ""
    except ValueError:
        detail = raw_resp.reason
    except Exception:
        pass

    detail = detail if detail else await raw_resp.text()

    raise YouWolException(status_code=raw_resp.status, detail=detail, **kwargs)
