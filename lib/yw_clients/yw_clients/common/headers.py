# standard library
import itertools
import json

from collections.abc import Callable

# third parties
from starlette.datastructures import Headers
from starlette.requests import Request

flatten = itertools.chain.from_iterable


class YouwolHeaders:
    """
    Gather headers and operations on headers related to Youwol.
    """

    #  About tracing & headers: https://www.w3.org/TR/trace-context/
    py_youwol_local_only: str = "py-youwol-local-only"
    """
    If this header is true, no operation involving the remote ecosystem is enabled.
    """
    youwol_origin: str = "youwol-origin"
    correlation_id: str = "x-correlation-id"
    """
    Correlation id (see [trace & context](https://www.w3.org/TR/trace-context/)).
    """
    trace_id: str = "x-trace-id"
    """
    Trace id (see [trace & context](https://www.w3.org/TR/trace-context/)).
    """

    trace_labels: str = "x-trace-labels"
    """
    Labels to associate with the trace, provided as a JSON array.
    """

    trace_attributes: str = "x-trace-attributes"
    """
    Attributes to associate with the trace, provided as a JSON dict.
    """

    py_youwol_port: str = "py-youwol-port"
    """
    Convey the port on which py-youwol is serving on `local-host`.
    """

    backends_partition: str = "x-backends-partition"
    """
    Target partition regarding backends calls.
    """

    @staticmethod
    def get_correlation_id(request: Request) -> str | None:
        """

        Parameters:
            request: Incoming request.
        Return:
            Correlation id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.correlation_id, None)

    @staticmethod
    def get_trace_id(request: Request) -> str | None:
        """

        Parameters:
            request: Incoming request.
        Return:
            Trace id of the request, if provided.
        """
        return request.headers.get(YouwolHeaders.trace_id, None)

    @staticmethod
    def get_trace_labels(request: Request) -> list[str]:
        """

        Parameters:
            request: Incoming request.

        Return:
            Trace's labels from the request's headers, if provided.

        Raise:
            `ValueError` when decoding the label header failed.
        """
        raw = request.headers.get(YouwolHeaders.trace_labels, "[]")
        labels = json.loads(raw)
        if not isinstance(labels, list):
            raise ValueError("Trace label's header should be provided as an array.")
        return [str(label) for label in labels]

    @staticmethod
    def get_trace_attributes(request: Request) -> dict[str, int | str | bool]:
        """

        Parameters:
            request: Incoming request.

        Return:
            Trace's attributes from the request's headers, if provided.

        Raise:
            `ValueError` when decoding the attribute header failed.
        """
        raw = request.headers.get(YouwolHeaders.trace_attributes, "{}")

        attributes = json.loads(raw)
        if not isinstance(attributes, dict):
            raise ValueError(
                "Trace attribute's header should be provided as a dictionary."
            )
        return attributes

    @staticmethod
    def get_py_youwol_local_only(request: Request) -> str | None:
        """

        Parameters:
            request: Incoming request.
        Return:
            The value of the header 'py-youwol-local-only' if included in the request.
        """
        return request.headers.get(YouwolHeaders.py_youwol_local_only, None)

    @staticmethod
    def get_backends_partition(request: Request, default_id: str | None) -> str | None:
        """

        Parameters:
            request: Incoming request.
            default_id: Default partition id to use if no partition id is provided.
        Return:
            Target partition ID, if available.
        """
        return request.headers.get(YouwolHeaders.backends_partition, default_id)


def generate_headers_downstream(
    incoming_headers: Headers,
    from_req_fwd: Callable[[list[str]], list[str]] = lambda _keys: [],
):
    # the following headers are set when a request is sent anyway
    black_list = ["content-type", "content-length", "content-encoding"]
    headers_keys = [h.lower() for h in incoming_headers.keys()]
    to_propagate = [h.lower() for h in from_req_fwd(headers_keys)] + [
        "authorization",
        YouwolHeaders.py_youwol_local_only,
        YouwolHeaders.backends_partition,
    ]

    return {
        k: v
        for k, v in incoming_headers.items()
        if k.lower() in to_propagate and k.lower() not in black_list
    }
