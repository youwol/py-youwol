# standard library
import builtins

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum

# typing
from typing import Any, NamedTuple, TypeVar, Union

# third parties
from pydantic import BaseModel

# relative
from ..clients.assets_gateway.assets_gateway import AssetsGatewayClient
from ..clients.cdn_sessions_storage import CdnSessionsStorageClient
from ..types import JSON

JsonLike = Union[JSON, BaseModel]
"""
Represents data structures that can be serialized into a json representation
(can also be `JSON` referencing `BaseModel`).
"""


class LogLevel(str, Enum):
    """
    Available severities when loging.
    """

    DEBUG = "DEBUG"
    """
    See [debug](@yw-nav-meth:Context.debug).
    """

    INFO = "INFO"
    """
    See [info](@yw-nav-meth:Context.info).
    """

    WARNING = "WARNING"
    """
    See [warning](@yw-nav-meth:Context.warning).
    """

    ERROR = "ERROR"
    """
    See [error](@yw-nav-meth:Context.error).
    """

    DATA = "DATA"
    """
    See [send](@yw-nav-meth:Context.send).
    """


class Label(Enum):
    STARTED = "STARTED"
    STATUS = "STATUS"
    INFO = "INFO"
    LOG = "LOG"
    APPLICATION = "APPLICATION"
    LOG_INFO = "LOG_INFO"
    LOG_DEBUG = "LOG_DEBUG"
    LOG_ERROR = "LOG_ERROR"
    LOG_WARNING = "LOG_WARNING"
    LOG_ABORT = "LOG_ABORT"
    DATA = "DATA"
    DONE = "DONE"
    EXCEPTION = "EXCEPTION"
    FAILED = "FAILED"
    FUTURE = "FUTURE"
    FUTURE_SUCCEEDED = "FUTURE_SUCCEEDED"
    FUTURE_FAILED = "FUTURE_FAILED"
    MIDDLEWARE = "MIDDLEWARE"
    API_GATEWAY = "API_GATEWAY"
    ADMIN = "ADMIN"
    END_POINT = "END_POINT"
    TREE_DB = "TREE_DB"
    START_BACKEND_SH = "START_BACKEND_SH"
    INSTALL_BACKEND_SH = "INSTALL_BACKEND_SH"


T = TypeVar("T")

TContextAttr = int | str | bool
"""
Allowed [context](@yw-nav-class:Context)'s attribute types.
"""


class LogEntry(NamedTuple):
    """
    LogEntry represents a log, they are created from the class
    [Context](@yw-nav-class:ContextReporter) when
    [starting function](@yw-nav-meth:Context.start) or
    [end-point](@yw-nav-meth:Context.start_ep) as well as
    when logging information (e.g. [info](@yw-nav-meth:Context.info)).

    Log entries are processed by [ContextReporter](@yw-nav-class:ContextReporter) that
    implements the action to trigger when a log entry is created.
    """

    level: LogLevel
    """
    Level (e.g. debug, info, error, *etc.*).
    """

    text: str
    """
    Text.
    """

    data: JSON
    """
    Data associated to the log (set up with the `data` argument of *e.g.*
    [info](@yw-nav-meth:Context.info)).
    """
    labels: list[str]
    """
    Labels associated to the log (set up with the `labels` argument of *e.g.*
    [info](@yw-nav-meth:Context.info)).
    """
    attributes: builtins.dict[str, TContextAttr]
    """
    Attributes associated to the log (set up with the `attributes` argument of *e.g.*
    [info](@yw-nav-meth:Context.info)).
    """
    context_id: str
    """
    The context ID that was used to generated this entry.
    """
    parent_context_id: str | None
    """
    The parent context ID that was used to generated this entry.
    """

    trace_uid: str | None
    """
    Trace ID (*i.e.*  root context ID).
    """

    timestamp: float
    """
    Timestamp: time in second since EPOC.
    """

    def dict(self):
        return {
            "level": self.level.name,
            "attributes": self.attributes,
            "labels": self.labels,
            "text": self.text,
            "data": self.data,
            "contextId": self.context_id,
            "parentContextId": self.parent_context_id,
            "timestamp": self.timestamp,
            "traceUid": self.trace_uid,
        }


DataType = Union[T, Callable[[], T], Callable[[], Awaitable[T]]]
"""
Type definition of context's data attribute.
"""


class ContextReporter(ABC):
    """
    Abstract class that implements log strategy (e.g. within terminal, file, REST call, *etc.*).
    """

    @abstractmethod
    async def log(self, entry: LogEntry):
        """
        Parameters:
            entry: the og entry to process
        """
        return NotImplemented


def format_message(entry: LogEntry):
    return {
        "level": entry.level.name,
        "attributes": entry.attributes,
        "labels": entry.labels,
        "text": entry.text,
        "data": entry.data,
        "contextId": entry.context_id,
        "parentContextId": entry.parent_context_id,
    }


StringLike = Any


HeadersFwdSelector = Callable[[list[str]], list[str]]
"""
A selector function for headers: it takes a list of header's keys in argument, and return the selected keys from it.
"""


LabelsGetter = Callable[[], set[str]]
"""
Type definition of a Label definition, used in [ContextFactory](@yw-nav-class:ContextFactory).
"""


@dataclass(frozen=True)
class ProxiedBackendCtxEnv:
    """
    Type of the [Context.env](@yw-nav-attr:Context.env) attribute for
    [ProxiedBackendContext](@yw-nav-glob:ProxiedBackendContext)
    specialization of [Context](@yw-nav-class:Context).

    """

    assets_gateway: AssetsGatewayClient
    """
    HTTP client.
    """
    sessions_storage: CdnSessionsStorageClient
    """
    HTTP client.
    """
