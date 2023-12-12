# standard library
from dataclasses import dataclass

# Youwol utilities
from youwol.utils.clients.request_executor import RequestExecutor, json_reader


@dataclass(frozen=True)
class AccountsClient:
    url_base: str

    request_executor: RequestExecutor

    async def healthz(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/healthz",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_session_details(self, **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/session",
            default_reader=json_reader,
            **kwargs,
        )
