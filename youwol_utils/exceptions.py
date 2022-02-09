from typing import Any, List, Dict

from aiohttp import ClientResponse
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse


class YouWolException(HTTPException):
    exceptionType = "YouWolException"

    def __init__(self, status_code: int, detail: Any, **kwargs):
        HTTPException.__init__(self, status_code=status_code, detail=detail)
        self.exceptionType = YouWolException.exceptionType


class PublishPackageError(YouWolException):
    exceptionType = "PublishPackageError"

    def __init__(self, context: str, **kwargs):
        YouWolException.__init__(
            self,
            status_code=422,
            detail={
                "context": context
            },
            **kwargs)
        self.exceptionType = PublishPackageError.exceptionType
        self.context = context

    def __str__(self):
        return f"""The package can not be published: {self.context}"""


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


class IndirectPackagesNotFound(YouWolException):
    exceptionType = "IndirectPackagesNotFound"

    def __init__(self, context: str, paths: Dict[str, List[str]], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={
                "context": context,
                "paths": paths
            },
            **kwargs)
        self.exceptionType = IndirectPackagesNotFound.exceptionType
        self.paths = paths
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; paths: {self.paths}"""


class CircularDependencies(YouWolException):
    exceptionType = "CircularDependencies"

    def __init__(self, context: str, packages: Dict[str, List[str]], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={
                "context": context,
                "packages": packages
            },
            **kwargs)
        self.exceptionType = CircularDependencies.exceptionType
        self.packages = packages
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; Packages: {self.packages}"""


YouwolExceptions = [
    PublishPackageError,
    PackagesNotFound,
    IndirectPackagesNotFound,
    CircularDependencies
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
