# typing
from typing import Any

# third parties
from aiohttp import ClientResponse, ContentTypeError
from starlette.exceptions import HTTPException

# Youwol clients
from yw_clients.common.json_utils import AnyDict


class YouWolException(HTTPException):
    """
    Base class for handled exceptions within YouWol: they usually correspond to errors originated from wrong user inputs
    (e.g. requesting a non-existent resource).

    If not caught, they end up being converted into a JSON response by the function
    :func:`youwol_exception_handler <youwol.utils.exceptions.youwol_exception_handler>`.

    When these exceptions propagate through services, they are wrapped using
    :class:`UpstreamResponseException <yw_clients.http.exceptions.UpstreamResponseException>`: its
    `detail` attribute presents a recursive
    structure that depicts the chain of calls within the services from which the exception happened
    (see :func:`upstream_exception_from_response <yw_clients.http.exceptions.upstream_exception_from_response>`).

    """

    exceptionType = "YouWolException"

    def __init__(self, status_code: int, detail: Any, **_):
        HTTPException.__init__(self, status_code=status_code, detail=detail)
        # pylint: disable-next=invalid-name
        self.exceptionType = YouWolException.exceptionType

    def __str__(self):
        return f"""{self.status_code} : {self.detail}"""


class UpstreamResponseException(YouWolException):
    """
    Represents an exception that has been generated from an HTTP call to a service.

    They are most of the time created using the function
    :func:`upstream_exception_from_response <yw_clients.http.exceptions.upstream_exception_from_response>`.

    It is common that the underlying exception being itself an
    :class:`UpstreamResponseException <yw_clients.http.exceptions.UpstreamResponseException>`, such that
    the `detail` attribute of the class presents a recursive structure that depicts the callstack of
    services from which the original exception initiated.
    """

    ManagedExceptions: list[type[YouWolException]] = []

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


async def upstream_exception_from_response(
    raw_resp: ClientResponse, **kwargs
) -> UpstreamResponseException:
    """
    Format an `UpstreamResponseException` from http responses.

    Parameters:
        raw_resp: Client response.
        kwargs: Forwarded to `UpstreamResponseException` constructor.
    """
    resp = None

    try:
        resp = await raw_resp.json()
        if resp and "exceptionType" in resp:
            exception_type = next(
                (
                    e
                    for e in UpstreamResponseException.ManagedExceptions
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
