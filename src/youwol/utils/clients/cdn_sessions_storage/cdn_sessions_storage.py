# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils import JSON
from youwol.utils.clients.request_executor import RequestExecutor, json_reader


@dataclass(frozen=True)
class CdnSessionsStorageClient:
    url_base: str

    request_executor: RequestExecutor

    def base_path(self, package: str, key: str):
        return f"{self.url_base}/applications/{package}/{key}"

    async def get(self, package: str, key: str, **kwargs):
        return await self.request_executor.get(
            url=self.base_path(package, key),
            default_reader=json_reader,
            **kwargs,
        )

    async def post(self, package: str, key: str, body: JSON, **kwargs):
        return await self.request_executor.post(
            url=self.base_path(package, key),
            default_reader=json_reader,
            json=body,
            **kwargs,
        )
