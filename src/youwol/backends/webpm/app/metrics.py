# standard library
import re

# typing
from typing import Dict

# third parties
from prometheus_client import Counter, Gauge


class CountVersions:
    def __init__(self):
        self.__counters: Dict[str, Counter] = {}

    def inc(self, version: str):
        version_safe = re.sub(r"[^[a-zA-Z0-9_]", r"_", version)
        if version_safe not in self.__counters:
            self.__counters[version_safe] = Counter(
                f"webpm_cdn_client_js_{version_safe}",
                f"Nb of cdn-client.js of version {version} download",
            )
        self.__counters[version_safe].inc()


count_version = CountVersions()
count_download = Counter("webpm_cdn_client_js", "Nb of cdn-client.js download")
count_data_transferred = Counter(
    name="webpm_data_transferred",
    documentation="Bytes transferred from upstream resources",
)
gauge_concurrent_streaming = Gauge(
    name="webpm_concurrent_streaming",
    documentation="Nb of concurrent resources streaming",
)
count_root_redirection = Counter("webpm_root_redirection", "Nb of redirection from /")
