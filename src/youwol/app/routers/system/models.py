# standard library
from enum import Enum

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils import JSON, LogEntry
from youwol.utils.http_clients.cdn_backend import Library
from youwol.utils.utils_requests import FuturesResponse, FuturesResponseEnd


class FolderContentResp(BaseModel):
    """
    Describes a folder content.
    """

    files: list[str]
    """
    List of the path files name.
    """

    folders: list[str]
    """
    List of folders name.
    """


class FolderContentBody(BaseModel):
    """
    Body used to query folder content
    using [folder_content](@yw-nav-func:youwol.app.routers.system.router.folder_content).
    """

    path: str


class QueryRootLogsBody(BaseModel):
    fromTimestamp: int
    maxCount: int


class Log(BaseModel):
    """
    Base class for logs generated from a [context](@yw-nav-class:Context) object.
    """

    level: str
    """
    Log level (info, debug, warning, error).
    """

    attributes: dict[str, str]
    """
    Attributes associated to the log.
    """

    labels: list[str]
    """
    Labels associated to the log.
    """
    text: str
    """
    Message.
    """

    data: JSON | None
    """
    Eventual data.
    """

    contextId: str
    """
    ID of the context that was used to generate the log (see [Context](@yw-nav-class:Context)).
    """

    parentContextId: str | None
    """
    ID of the parent context of the context that was used to generate the log
    (see [Context](@yw-nav-class:Context)).
    """

    timestamp: float

    @staticmethod
    def from_log_entry(log_entry: LogEntry):
        return Log(
            level=log_entry.level.name,
            attributes=log_entry.attributes,
            labels=log_entry.labels,
            text=log_entry.text,
            data=log_entry.data,
            contextId=log_entry.context_id,
            parentContextId=log_entry.parent_context_id,
            timestamp=log_entry.timestamp,
        )


class LeafLogResponse(Log):
    """
    A leaf log corresponds to a message - there is no log that will have as
    [parentContextId](@yw-nav-attr:youwol.app.routers.system.models.Log.parentContextId)
    the [contextId](@yw-nav-attr:youwol.app.routers.system.models.Log.contextId) of this log.

    It is created when using *e.g.* [Context.info](@yw-nav-meth:Context.info).
    """


class NodeLogStatus(Enum):
    SUCCEEDED = "Succeeded"
    """
    The log has a succeeded status: it signals that the parent function has ran as expected.
    """

    FAILED = "Failed"
    """
    The log has a failed status: it signals that the parent function failed, the log content explains the reason.
    """

    UNRESOLVED = "Unresolved"
    """
    The log has a unresolved status: it signals that the parent function is unresolved yet, the log content
    explains the reason.
    """


class NodeLogResponse(Log):
    """
    A 'node' log is associated to a function execution, it is likely associated to children: the logs generated
    within the function.

    It is created when using *e.g.* [Context.start](@yw-nav-meth:Context.start).

    The children logs have as
    [parentContextId](@yw-nav-attr:youwol.app.routers.system.models.Log.parentContextId)
    the [contextId](@yw-nav-attr:youwol.app.routers.system.models.Log.contextId) of this log.
    """

    failed: bool
    """
    Whether the function has a failed status after leaving it (deprecated, see `status` attribute).
    """

    future: bool
    """
    Whether the log function a future status after leaving it (deprecated, see `status` attribute).
    """

    status: NodeLogStatus
    """
    Status of the function after leaving it.
    """


class LogsResponse(BaseModel):
    """
    Describes a list of logs.
    """

    logs: list[Log]


class NodeLogsResponse(BaseModel):
    """
    Describes a list of 'node' logs (associated to the execution of a function).
    """

    logs: list[NodeLogResponse]
    """
    Logs list
    """


class PostLogBody(Log):
    """
    Body for a single log description.
    """

    traceUid: str
    """
    This attribute is the root parent's context ID of the log (equivalent to the usual trace ID).
    """


class PostLogsBody(BaseModel):
    """
    Body of the end point defined by the function
     [post_logs](@yw-nav-func:youwol.app.routers.system.router.post_logs).
    """

    logs: list[PostLogBody]
    """
    List of the logs.
    """


class PostDataBody(BaseModel):
    """
    Body of the end point defined by the function
     [post_data](@yw-nav-func:youwol.app.routers.system.router.post_data).
    """

    data: list[PostLogBody]
    """
    List of the data.
    """


class BackendLogsResponse(BaseModel):
    logs: list[Log]
    server_outputs: list[str]
    install_outputs: list[str] | None


class UninstallResponse(BaseModel):
    """
    Response model when calling [uninstall](@yw-nav-func:youwol.app.routers.system.router.uninstall)
    """

    name: str
    """
    Backend name.
    """

    version: str
    """
    Backend version.
    """

    backendTerminated: bool
    """
    Whether the backend has been terminated (if it was running when uninstalled).
    """
    wasInstalled: bool
    """
    Whether the backend was already installed.
    """


class TerminateResponse(BaseModel):
    """
    Response model when calling [terminate](@yw-nav-func:youwol.app.routers.system.router.terminate)
    """

    name: str
    """
    Backend name.
    """

    version: str
    """
    Backend version.
    """

    wasRunning: bool
    """
    Whether the backend was running.
    """


class BackendInstallResponse(BaseModel):
    """
    Response model of a backend installation from
    [`/admin/system/backends/install`](system.router.install_graph).
    """

    name: str
    """
    The backend name.
    """
    version: str
    """
    The backend specific version.
    """
    exportedClientSymbol: str
    """
    Exported symbol of the client's bundle.
    """
    clientBundle: str
    """
    Client's bundle.
    """

    @staticmethod
    def from_lib_info(backend: Library):
        url_base = f"/backends/{backend.name}/{backend.version}"
        exported_symbol = f"{backend.name}_APIv{backend.apiKey}"
        return BackendInstallResponse(
            name=backend.name,
            version=backend.version,
            exportedClientSymbol=exported_symbol,
            clientBundle=f"""
return async ({{window, webpmClient, wsData$}}) => {{

    const {{rxjs, uuid}} = await webpmClient.install({{
        modules:["rxjs#^7.5.6 as rxjs", "uuid#^8.3.2 as uuid"]}})
    const {{switchMap, filter, takeWhile, from, ReplaySubject}} = rxjs
    const symbol = "{exported_symbol}"
    const resp$ = (url, options) => from(fetch(`{url_base}/${{url}}`, options))
    const respJson$ = (url, options) => resp$(url, options).pipe(
        switchMap((resp) => from(resp.json()))
    )
    const respText$ = (url, options) => resp$(url, options).pipe(
        switchMap((resp) => from(resp.text()))
    )
    window[symbol] = {{
        name: "{backend.name}",
        version: "{backend.version}",
        urlBase: "{url_base}",
        fetch: (url, options) => fetch(`{url_base}/${{url}}`),
        fromFetch:  (url, options) => resp$(url, options),
        fromFetchJson:  (url, options) => respJson$(url, options),
        fromFetchText:  (url, options) => respText$(url, options),
        stream: (url, options) => {{
            channelId = options?.channelId || `${{uuid.v4()}}`
            const resp$ = new ReplaySubject()
            wsData$.pipe(
                filter(({{labels, attributes}}) => {{
                    return labels.includes('AsyncTaskResult') &&
                    (
                        labels.includes(channelId) || // deprecated, use attributes instead (youwol>=0.1.9)
                        attributes[{FuturesResponse.channelIdKey}] === channelId
                    )
                }}),
                takeWhile((m) => !m.labels.includes("{FuturesResponseEnd.__name__}"))
            ).subscribe(
                (d) => {{resp$.next(d)}},
                (e) => console.error(e),
                () => resp$.complete()
            )
            return respJson$(url+`?channel-id=${{channelId}}`, options).pipe(
                switchMap(({{channelId}}) => {{
                    return resp$
                }}),
            )
        }}
    }}
}}
""",
        )


class BackendsGraphInstallResponse(BaseModel):
    """
    Response model of [`/admin/system/backends/install`](system.router.install_graph).
    """

    backends: list[BackendInstallResponse]
