# standard library
from dataclasses import dataclass, field

# typing
from typing import Dict

# third parties
import aiohttp

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response


@dataclass(frozen=True)
class FluxClient:
    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    async def get_projects(self, **kwargs):
        url = f"{self.url_base}/projects"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def create_project(self, body, **kwargs):
        url = f"{self.url_base}/projects/create"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def upload_project(self, data, project_id: str = None, **kwargs):
        url = f"{self.url_base}/projects/upload"
        params = kwargs["params"] if "params" in kwargs else {}
        params = {**params, "project-id": project_id} if project_id else params
        kwargs["params"] = params

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, data=data, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def download_zip(self, project_id: str = None, **kwargs):
        url = f"{self.url_base}/projects/{project_id}/download-zip"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.read()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def update_project(self, project_id, body, **kwargs):
        url = f"{self.url_base}/projects/{project_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_project(self, project_id: str, **kwargs):
        url = f"{self.url_base}/projects/{project_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def delete_project(self, project_id: str, **kwargs):
        url = f"{self.url_base}/projects/{project_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_records(self, body, **kwargs):
        url = f"{self.url_base}/records"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def update_metadata(self, project_id: str, body, **kwargs):
        url = f"{self.url_base}/projects/{project_id}/metadata"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def get_metadata(self, project_id: str, **kwargs):
        url = f"{self.url_base}/projects/{project_id}/metadata"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def duplicate(self, project_id: str, **kwargs):
        url = f"{self.url_base}/projects/{project_id}/duplicate"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)

    async def publish_application(self, project_id: str, body, **kwargs):
        url = f"{self.url_base}/projects/{project_id}/publish-application"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await raise_exception_from_response(resp, **kwargs)
