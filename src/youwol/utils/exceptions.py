# standard library
import traceback

# typing
from typing import Any

# third parties
from aiohttp import ClientResponse, ContentTypeError
from fastapi import HTTPException, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse

# Youwol utilities
from youwol.utils.types import AnyDict


class YouWolException(HTTPException):
    """
    Base class for handled exceptions within YouWol: they usually correspond to errors originated from wrong user inputs
    (e.g. requesting a non-existent resource).

    If not caught, they end up being converted into a JSON response by the function
    [youwol_exception_handler](@yw-nav-func:youwol.utils.exceptions.youwol_exception_handler).

    When these exceptions propagate through services, they are wrapped using
    [UpstreamResponseException](@yw-nav-class:youwol.utils.exceptions.UpstreamResponseException): its
    [detail attribute](@yw-nav-attr:youwol.utils.exceptions.UpstreamResponseException.detail) present a recursive
    structure that depicts the chain of calls within the services from which the exception happened
    (see [upstream_exception_from_response](@yw-nav-func:youwol.utils.exceptions.upstream_exception_from_response)).

    """

    exceptionType = "YouWolException"

    def __init__(self, status_code: int, detail: Any, **_):
        HTTPException.__init__(self, status_code=status_code, detail=detail)
        self.exceptionType = YouWolException.exceptionType

    def __str__(self):
        return f"""{self.status_code} : {self.detail}"""


class ServerError(YouWolException):
    exceptionType = "ServerError"

    def __init__(self, detail: Any, **kwargs):
        YouWolException.__init__(self, status_code=500, detail=detail, **kwargs)
        self.exceptionType = ServerError.exceptionType
        self.detail = detail

    def __str__(self):
        return f"""{self.status_code} : {self.detail}"""


class PublishPackageError(YouWolException):
    exceptionType = "PublishPackageError"

    def __init__(self, context: str, **kwargs):
        YouWolException.__init__(
            self, status_code=422, detail={"context": context}, **kwargs
        )
        self.exceptionType = PublishPackageError.exceptionType
        self.context = context

    def __str__(self):
        return f"""The package can not be published: {self.context}"""


class PackagesNotFound(YouWolException):
    exceptionType = "PackagesNotFound"

    def __init__(self, context: str, packages: list[str], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "packages": packages},
            **kwargs,
        )
        self.exceptionType = PackagesNotFound.exceptionType
        self.packages = packages
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; Packages: {self.packages}"""


class IndirectPackagesNotFound(YouWolException):
    exceptionType = "IndirectPackagesNotFound"

    def __init__(self, context: str, paths: dict[str, list[str]], **kwargs):
        YouWolException.__init__(
            self, status_code=404, detail={"context": context, "paths": paths}, **kwargs
        )
        self.exceptionType = IndirectPackagesNotFound.exceptionType
        self.paths = paths
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; paths: {self.paths}"""


class DependencyErrorData(BaseModel):
    key: str
    path: list[str]
    detail: str


class DependenciesError(YouWolException):
    exceptionType = "DependenciesError"

    def __init__(self, context: str, errors: list[dict[str, Any]], **kwargs):
        """

        :param context: context of the error
        :param errors: An error as a dict like {'key':str, 'paths': List[str], 'detail': str}
        :param kwargs: forwarding arguments to YouWolException
        """
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "errors": errors},
            **kwargs,
        )
        self.exceptionType = DependenciesError.exceptionType
        self.context = context

    def __str__(self):
        return f"""Dependencies not found. Error: {self.detail}"""


class CircularDependencies(YouWolException):
    exceptionType = "CircularDependencies"

    def __init__(self, context: str, packages: dict[str, list[AnyDict]], **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "packages": packages},
            **kwargs,
        )
        self.exceptionType = CircularDependencies.exceptionType
        self.packages = packages
        self.context = context

    def __str__(self):
        return f"""Packages not found. Context: {self.context}; Packages: {self.packages}"""


class ProjectNotFound(YouWolException):
    exceptionType = "ProjectNotFound"

    def __init__(self, context: str, project: str, **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "project": project},
            **kwargs,
        )
        self.exceptionType = ProjectNotFound.exceptionType
        self.project = project
        self.context = context

    def __str__(self):
        return f"""Project '{self.project}' not found in workspace. Context: {self.context}"""


class PipelineStepNotFound(YouWolException):
    exceptionType = "PipelineStepNotFound"

    def __init__(self, context: str, project: str, step: str, **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "project": project, "step": step},
            **kwargs,
        )
        self.exceptionType = PipelineStepNotFound.exceptionType
        self.project = project
        self.step = step
        self.context = context

    def __str__(self):
        return f"""Pipeline's step '{self.step}' not found in project '{self.project}'. Context: {self.context}"""


class PipelineFlowNotFound(YouWolException):
    exceptionType = "PipelineFlowNotFound"

    def __init__(self, context: str, project: str, flow: str, **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "project": project, "flow": flow},
            **kwargs,
        )
        self.exceptionType = PipelineFlowNotFound.exceptionType
        self.project = project
        self.flow = flow
        self.context = context

    def __str__(self):
        return f"""Pipeline's flow '{self.flow}' not found in project '{self.project}'. Context: {self.context}"""


class FolderNotFound(YouWolException):
    exceptionType = "FolderNotFound"

    def __init__(self, context: str, folder: str, **kwargs):
        YouWolException.__init__(
            self,
            status_code=404,
            detail={"context": context, "folder": folder},
            **kwargs,
        )
        self.exceptionType = FolderNotFound.exceptionType
        self.context = context
        self.folder = folder

    def __str__(self):
        return f"""The folder '{self.folder}' is not found. Context: {self.context}"""


class ResourcesNotFoundException(YouWolException):
    exceptionType = "ResourcesNotFoundException"

    def __init__(self, path: str, detail: str = "", **kwargs):
        YouWolException.__init__(
            self, status_code=404, detail={"path": path, "detail": detail}, **kwargs
        )
        self.path = path
        self.exceptionType = ResourcesNotFoundException.exceptionType

    def __str__(self):
        return f"""The resource at path '{self.path}' is not a file."""


class QueryIndexException(YouWolException):
    exceptionType = "QueryIndexException"

    def __init__(self, query: str, error: Any, **kwargs):
        YouWolException.__init__(
            self, status_code=404, detail={"query": query, "error": error}, **kwargs
        )
        self.query = query
        self.error = error
        self.exceptionType = QueryIndexException.exceptionType

    def __str__(self):
        return (
            f"""The query '{self.query}' resolved to unexpected result: ${self.error}"""
        )


class InvalidInput(YouWolException):
    exceptionType = "InvalidInput"

    def __init__(self, error: str, **kwargs):
        YouWolException.__init__(
            self, status_code=422, detail={"error": error}, **kwargs
        )
        self.error = error
        self.exceptionType = InvalidInput.exceptionType

    def __str__(self):
        return f"""Invalid input: {self.error}"""


class UpstreamResponseException(YouWolException):
    """
    Represents an exception that has been generated from an HTTP call to a service.

    They are most of the time created using the function
    [upstream_exception_from_response](@yw-nav-func:youwol.utils.exceptions.upstream_exception_from_response).

    It is common that the underlying exception being itself an
    [UpstreamResponseException](@yw-nav-class:youwol.utils.exceptions.UpstreamResponseException), such that
    the `detail` attribute of the class presents a recursive structure that depicts the callstack of
    services from which the original exception initiated.
    """

    exceptionType = "UpstreamResponseException"

    # do not change case in 'exceptionType': UpstreamResponseException needs to be
    # 'auto-constructable' from its details
    def __init__(
        self, status: int, url: str, detail: Any, exceptionType: str, **kwargs: AnyDict
    ):  # NOSONAR
        """
        Initialize a new instance.

        Parameters:
            status: [Status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status).
            url: URL of the HTTP call
            detail: Details of the exception
            exceptionType: Class name of the exception
            kwargs: keywords arguments forwarded to the base class constructor.
        """
        super().__init__(
            status_code=status,
            detail={
                "url": url,
                "status": status,
                "exceptionType": exceptionType,
                "detail": detail,
            },
            **kwargs,
        )
        self.exceptionType = UpstreamResponseException.exceptionType

    def __str__(self):
        return """Upstream Exception"""


YouwolExceptions: list[type[YouWolException]] = [
    ServerError,
    PipelineFlowNotFound,
    FolderNotFound,
    PipelineStepNotFound,
    ProjectNotFound,
    PublishPackageError,
    PackagesNotFound,
    IndirectPackagesNotFound,
    DependenciesError,
    CircularDependencies,
    ResourcesNotFoundException,
    QueryIndexException,
    InvalidInput,
    UpstreamResponseException,
]


async def youwol_exception_handler(
    request: Request, exc: YouWolException
) -> JSONResponse:
    """
    Handler for [YouWolException](@yw-nav-class:youwol.utils.exceptions.YouWolException).
    Those are somehow 'expected' exceptions, due to for instance a wrong inputs when calling an HTTP endpoint.

    No bug report is proposed in this case (by opposition to
    [unexpected_exception_handler](@yw-nav-func:youwol.utils.exceptions.unexpected_exception_handler)).

    Parameters:
        request: Associated request from which the exception happened.
        exc: The exception generated.

    Return:
        JSON representation of the exception.
    """
    if request.state and request.state.context:
        await request.state.context.info("Trigger youwol_exception_handler")
    content = {
        "url": request.url.path,
        "exceptionType": exc.exceptionType,
        "detail": exc.detail,
    }
    return JSONResponse(status_code=exc.status_code, content=content)


async def unexpected_exception_handler(request: Request, exc: Exception):
    """
    Handler for [Exception](https://docs.python.org/3/library/exceptions.html#Exception) that are not
    [YouWolException](@yw-nav-class:youwol.utils.exceptions.YouWolException).

    Those are somehow 'unexpected' exceptions, due to for instance a default in code implementation.

    When reaching this point, a bug report is proposed.

    Parameters:
        request: Associated request from which the exception happened.
        exc: The exception generated.

    Return:
        JSON representation of the exception.
    """

    if request.state and request.state.context:
        await request.state.context.info("Trigger youwol_developer_exception_handler")
    print(traceback.format_exc())
    print(
        "Please fill a new issue (https://github.com/youwol/py-youwol/issues) by providing the above stack trace.\n"
    )
    return PlainTextResponse(
        status_code=500,
        content=f"Exception in implementation caught: \n {exc}\n"
        f"Refer to the py-youwol terminal for stack trace.",
    )


async def upstream_exception_from_response(
    raw_resp: ClientResponse, **kwargs
) -> UpstreamResponseException:
    resp = None

    try:
        resp = await raw_resp.json()
        if resp and "exceptionType" in resp:
            exception_type = next(
                (
                    e
                    for e in YouwolExceptions
                    if e.exceptionType == resp["exceptionType"]
                ),
                None,
            )
            if exception_type:
                upstream_exception0 = exception_type(**resp["detail"])
                return UpstreamResponseException(
                    url=raw_resp.url.human_repr(),
                    status=upstream_exception0.status_code,
                    detail=upstream_exception0.detail,
                    exceptionType=upstream_exception0.exceptionType,
                )

    except (ValueError, ContentTypeError):
        pass

    detail = resp and (
        resp.get("detail", None) or resp.get("message", None) or raw_resp.reason
    )
    detail = detail if detail else await raw_resp.text()

    return UpstreamResponseException(
        url=raw_resp.url.human_repr(),
        status=raw_resp.status,
        detail=detail,
        exceptionType="HTTP",
        **{
            k: v
            for k, v in kwargs.items()
            if k not in ["url", "status", "detail", "exceptionType"]
        },
    )
