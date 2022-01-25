import json
import time
from dataclasses import dataclass
from typing import Union, Dict, List, Optional

from pydantic import BaseModel
from starlette.websockets import WebSocket

from youwol_utils import to_json, JSON
from youwol_utils.context import WsContextLogger, ContextLogger, LogEntry, Label


@dataclass(frozen=False)
class WebSocketsStore:
    userChannel: Union[WebSocket, None] = None


def web_socket_cache():
    return WebSocketsStore


class Log(BaseModel):
    level: str
    attributes: Dict[str, str]
    labels: List[str]
    text: str
    data: Optional[JSON]
    contextId: str
    parentContextId: Optional[str]
    timestamp: int


class AdminContextLogger(ContextLogger):
    max_count = 10000

    root_node_logs: List[Log] = []
    node_logs: List[Log] = []
    leaf_logs: List[Log] = []

    errors = set()

    def __init__(self):
        super()

    def resize_if_needed(self, items: List[any]):
        if len(items) > 2 * self.max_count:
            return items[len(items) - self.max_count:]
        return items

    async def log(self, entry: LogEntry):
        try:
            data = to_json(entry.data) if isinstance(entry.data, BaseModel) else entry.data
            _text = json.dumps(data)
        except (TypeError, OverflowError):
            print("error in JSON serialization")
            return

        message = {
            "level": entry.level.name,
            "attributes": entry.attributes,
            "labels": [label for label in entry.labels],
            "text": entry.text,
            "data": data,
            "contextId": entry.context_id,
            "parentContextId": entry.parent_context_id,
            "timestamp": time.time() * 1e6
        }

        if str(Label.STARTED) in entry.labels and entry.parent_context_id == 'root':
            self.root_node_logs.append(Log(**message))

        if str(Label.STARTED) in entry.labels and entry.parent_context_id != 'root':
            self.node_logs.append(Log(**message))

        if str(Label.STARTED) not in entry.labels:
            self.leaf_logs.append(Log(**message))

        if str(Label.FAILED) in entry.labels:
            self.errors.add(entry.context_id)

        self.root_node_logs = self.resize_if_needed(self.root_node_logs)
        self.leaf_logs = self.resize_if_needed(self.leaf_logs)


class UserContextLogger(WsContextLogger):
    def __init__(self):
        super().__init__(lambda: [WebSocketsStore.userChannel])
