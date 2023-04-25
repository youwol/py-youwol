# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class StoriesClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    async def healthz(self, **kwargs):
        url = f"{self.url_base}/healthz"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp
                await raise_exception_from_response(resp, **kwargs)

    async def docs(self, **kwargs):
        url = f"{self.url_base}/docs"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp
                await raise_exception_from_response(resp, **kwargs)

    async def create_story(self, body, **kwargs):
        url = f"{self.url_base}/stories"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def publish_story(self, data, **kwargs):
        url = f"{self.url_base}/stories"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, data=data, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def download_zip(self, story_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/download-zip"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.read()
                await raise_exception_from_response(resp, **kwargs)

    async def get_story(self, story_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def update_story(self, story_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def delete_story(self, story_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_global_contents(self, story_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/global-contents"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def post_global_contents(self, story_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/global-contents"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_children(
        self,
        story_id: str,
        parent_document_id: str,
        from_index=float,
        count=int,
        **kwargs,
    ):
        params = {"from-index": from_index, "count": count}
        url = f"{self.url_base}/stories/{story_id}/documents/{parent_document_id}/children"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, params=params, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_content(self, story_id: str, content_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/contents/{content_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def set_content(self, story_id: str, content_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/contents/{content_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.text()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_document(self, story_id: str, document_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/documents/{document_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def create_document(self, story_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/documents"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def delete_document(self, story_id: str, document_id: str, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/documents/{document_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def update_document(self, story_id: str, document_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/documents/{document_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def move_document(self, story_id: str, document_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/documents/{document_id}/move"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def add_plugin(self, story_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/plugins"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def upgrade_plugins(self, story_id: str, body, **kwargs):
        url = f"{self.url_base}/stories/{story_id}/plugins/upgrade"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)
