# third parties
import pytest

# Youwol clients
from yw_clients import AioHttpExecutor, EmptyResponse, YouwolHeaders
from yw_clients.http.cdn_sessions_storage import CdnSessionsStorageClient

headers = {YouwolHeaders.py_youwol_local_only: "true"}


@pytest.mark.asyncio
class TestCdnSessionsStorageClient:
    client = CdnSessionsStorageClient(
        url_base="http://localhost:2001/api/cdn-sessions-storage",
        request_executor=AioHttpExecutor(),
    )

    async def test_api(self) -> None:
        post_resp = await self.client.post(
            package="test-package", key="foo", body={"value": 42}, headers=headers
        )
        assert isinstance(post_resp, EmptyResponse)
        get_resp = await self.client.get(
            package="test-package", key="foo", headers=headers
        )
        assert isinstance(get_resp, dict)
