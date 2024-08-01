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
    See :meth:`debug <youwol.utils.context.context.Context.debug>`.
    """

    INFO = "INFO"
    """
    See :meth:`info <youwol.utils.context.context.Context.info>`.
    """

    WARNING = "WARNING"
    """
    See :meth:`warning <youwol.utils.context.context.Context.warning>`.
    """

    ERROR = "ERROR"
    """
    See :meth:`error <youwol.utils.context.context.Context.error>`.
    """

    DATA = "DATA"
    """
    See :meth:`send <youwol.utils.context.context.Context.send>`.
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
    STD_OUTPUT = "STD_OUTPUT"
    ESM_SERVER = "ESM_SERVER"
    DISPATCH_ESM_SERVER = "DISPATCH_ESM_SERVER"


T = TypeVar("T")

TContextAttr = int | str | bool
"""
Allowed :class:`context <youwol.utils.context.context.Context>`'s attribute types.
"""


class LogEntry(NamedTuple):
    """
    LogEntry represents a log, they are created from the class
    :class:`Context <youwol.utils.context.models.ContextReporter>` when
    :meth:`starting function <youwol.utils.context.context.Context.start>` or
    :meth:`end-point <youwol.utils.context.context.Context.start_ep>` as well as
    when logging information (e.g. :meth:`info <youwol.utils.context.context.Context.info>`).

    Log entries are processed by :class:`WsContextReporter <youwol.utils.context.reporter.WsContextReporter>` that
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
    :meth:`info <youwol.utils.context.context.Context.info>`).
    """
    labels: list[str]
    """
    Labels associated to the log (set up with the `labels` argument of *e.g.*
    :meth:`info <youwol.utils.context.context.Context.info>`).
    """
    attributes: builtins.dict[str, TContextAttr]
    """
    Attributes associated to the log (set up with the `attributes` argument of *e.g.*
    :meth:`info <youwol.utils.context.context.Context.info>`).
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
Type definition of a Label definition, used in :class:`ContextFactory <youwol.utils.context.context.ContextFactory>`.
"""


@dataclass(frozen=True)
class ProxiedBackendCtxEnv:
    """
    Type of the :attr:`Context.env <youwol.utils.context.context.Context.env>` attribute for
    :glob:`ProxiedBackendContext <youwol.utils.context.context.ProxiedBackendContext>`
    specialization of :class:`Context <youwol.utils.context.context.Context>`.

    """

    assets_gateway: AssetsGatewayClient
    """
    HTTP client.
    """
    sessions_storage: CdnSessionsStorageClient
    """
    HTTP client.
    """
