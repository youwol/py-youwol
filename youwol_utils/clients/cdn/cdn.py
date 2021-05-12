import hashlib

from dataclasses import field, dataclass
from pathlib import Path
from typing import Dict, Union, List
import aiohttp

from youwol_utils.clients import raise_exception_from_response


def md5_update_from_file(filename: Union[str, Path], current_hash):
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            current_hash.update(chunk)
    return current_hash


def files_check_sum(paths: List[Path]):

    sha_hash = hashlib.md5()

    for path in sorted(paths, key=lambda p: str(p).lower()):
        sha_hash.update(path.name.encode())
        sha_hash = md5_update_from_file(path, sha_hash)
    sha_hash = sha_hash.hexdigest()
    return sha_hash


@dataclass(frozen=True)
class CdnClient:

    url_base: str

    headers: Dict[str, str] = field(default_factory=lambda: {})

    @property
    def packs_url(self):
        return f"{self.url_base}/queries/flux-packs"

    @property
    def libraries_url(self):
        return f"{self.url_base}/queries/libraries"

    @property
    def dependencies_url(self):
        return f"{self.url_base}/queries/dependencies-latest"

    @property
    def loading_graph_url(self):
        return f"{self.url_base}/queries/loading-graph"

    @property
    def publish_url(self):
        return f"{self.url_base}/actions/publish-library"

    @property
    def push_url(self):
        return f"{self.url_base}/actions/sync"

    async def query_packs(self, namespace: str = None, **kwargs):

        url = self.packs_url if not namespace else f"{self.packs_url}?namespace={namespace}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.packs_url, headers=self.headers)

    async def query_libraries(self, **kwargs):

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.libraries_url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.libraries_url, headers=self.headers)

    async def query_dependencies_latest(self, libraries: List[str], **kwargs):

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=self.dependencies_url, json={"libraries": libraries}, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.dependencies_url, headers=self.headers)

    async def query_loading_graph(self, body: any, **kwargs):

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url=self.loading_graph_url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.loading_graph_url, headers=self.headers)

    async def get_json(self, url: Union[Path, str], **kwargs):

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=f"{self.url_base}/{str(url)}", **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=f"{self.url_base}/{str(url)}", headers=self.headers)

    async def get_library(self, library_id: str, version: str, **kwargs):

        url = f"{self.url_base}/libraries/{library_id}/{version}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def get_versions(self, library_id: str, **kwargs):

        url = f"{self.url_base}/libraries/{library_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def publish(self, zip_path: Union[Path, str], **kwargs):

        files = {'file': open(zip_path, 'rb')}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(self.publish_url, data=files, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.publish_url, headers=self.headers)

    async def sync(self, zip_path: Union[Path, str], **kwargs):

        files = {'file': open(zip_path, 'rb')}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(self.push_url, data=files, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.push_url, headers=self.headers)

    async def delete_version(self, library_name: str, version: str, **kwargs):

        url = f"{self.url_base}/libraries/{library_name}/{version}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.push_url, headers=self.headers)

    async def get_package(self, library_name: str, version: str, **kwargs):

        url = f"{self.url_base}/libraries/{library_name}/{version}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.read()
                await raise_exception_from_response(resp, url=self.push_url, headers=self.headers)

    async def get_records(self, body, **kwargs):

        url = f"{self.url_base}/records"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(url, json=body, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=self.push_url, headers=self.headers)
