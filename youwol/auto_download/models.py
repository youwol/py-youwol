

import pprint
import time
from abc import ABC
from dataclasses import dataclass
from itertools import groupby

Context = 'youwol.context.Context'


class DownloadLogger:

    messages = []

    async def info(self, process_id: str, title: str, **kwargs):
        self.messages.append({**{'title': title, 'time': time.time(), 'process_id': process_id, 'level': 'info'},
                              **kwargs})

    async def error(self, process_id: str, title: str, **kwargs):
        self.messages.append({**{'title': title, 'time': time.time(), 'process_id': process_id, 'level': 'error'},
                              **kwargs})

    def dumps(self):
        print("##### Dump logger")
        messages = sorted(self.messages, key=lambda _: _['time'])
        messages = sorted(messages, key=lambda _: _['process_id'])

        for k, g in groupby(messages, lambda _: _['process_id']):
            print("=> Process", k)
            for m in g:
                pprint.pprint(m)

        print("##### Done dump logger")
        self.messages = []


@dataclass
class DownloadTask(ABC):
    process_id: str
    raw_id: str
    asset_id: str
    url: str
    logger: DownloadLogger
    context: Context
