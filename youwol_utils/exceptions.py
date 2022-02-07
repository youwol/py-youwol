from typing import Any, List

from aiohttp import ClientResponse
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse


class YouWolException(HTTPException):
    exceptionType = "YouWolException"

    def __init__(self, status_code: int, detail: Any, **kwargs):
        HTTPException.__init__(self, status_code=status_code, detail=detail)
        self.exceptionType = YouWolException.exceptionType


class PackagesNotFound(YouWolException):
    exceptionType = "PackagesNotFound"

    def __init__(self, context: str, packages: List[str], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={
                "context": context,
                "packages": packages
            },
            **kwargs)
        self.exceptionType = PackagesNotFound.exceptionType
        self.packages = packages
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; Packages: {self.packages}"""


class CyclicDependencies(YouWolException):
    exceptionType = "CyclicDependencies"

    def __init__(self, context: str, packages: List[str], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={
                "context": context,
                "packages": packages
            },
            **kwargs)
        self.exceptionType = PackagesNotFound.exceptionType
        self.packages = packages
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; Packages: {self.packages}"""


YouwolExceptions = [
    PackagesNotFound,
    CyclicDependencies
]


async def youwol_exception_handler(request: Request, exc: YouWolException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "exceptionType": exc.exceptionType,
            "detail": exc.detail,
            "url": request.url.path
        }
    )


async def raise_exception_from_response(raw_resp: ClientResponse, **kwargs):
    parameters = {}
    resp = None

    try:
        resp = await raw_resp.json()
        if resp and "exceptionType" in resp:
            exception_type = next((e for e in YouwolExceptions if e.exceptionType == resp["exceptionType"]), None)
            if exception_type:
                raise exception_type(**resp['detail'])
    except ValueError:
        pass

    detail = resp.get("detail", None) or resp.get("message", None) or raw_resp.reason
    detail = detail if detail else await raw_resp.text()

    raise YouWolException(status_code=raw_resp.status, detail=detail, **{**kwargs, **parameters})
