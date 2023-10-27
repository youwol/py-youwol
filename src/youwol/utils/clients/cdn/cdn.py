# standard library
import functools
import hashlib

from dataclasses import dataclass, field
from pathlib import Path

# typing
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Union

# third parties
import aiohttp

from aiohttp import ClientResponse, FormData

# Youwol utilities
from youwol.utils.exceptions import raise_exception_from_response
from youwol.utils.utils_requests import extract_aiohttp_response


def md5_update_from_file(filename: Union[str, Path], current_hash):
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            current_hash.update(chunk)
    return current_hash


def files_check_sum(paths: Iterable[Path]):
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
        return f"{self.url_base}/publish-library"

    @property
    def download_url(self):
        return f"{self.url_base}/download-library"

    @property
    def push_url(self):
        return f"{self.url_base}/publish_libraries"

    async def query_packs(self, namespace: str = None, **kwargs):
        url = (
            self.packs_url
            if not namespace
            else f"{self.packs_url}?namespace={namespace}"
        )
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.packs_url, headers=self.headers
                )

    async def query_libraries(self, **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.libraries_url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.libraries_url, headers=self.headers
                )

    async def query_dependencies_latest(self, libraries: List[str], **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.dependencies_url, json={"libraries": libraries}, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.dependencies_url, headers=self.headers
                )

    async def query_loading_graph(self, body: any, **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.loading_graph_url, json=body, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.loading_graph_url, headers=self.headers
                )

    async def get_json(self, url: Union[Path, str], **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(
                url=f"{self.url_base}/{str(url)}", **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=f"{self.url_base}/{str(url)}", headers=self.headers
                )

    async def get_library_info(
        self, library_id: str, semver: str = None, max_count: int = None, **kwargs
    ):
        query_params = [
            (k, v)
            for k, v in {"semver": semver, "max-count": max_count}.items()
            if v is not None
        ]
        suffix = functools.reduce(
            lambda acc, item: acc + f"{acc}{item[0]}={item[1]}&", query_params, ""
        )

        url = f"{self.url_base}/libraries/{library_id}?{suffix}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def get_version_info(self, library_id: str, version: str, **kwargs):
        url = f"{self.url_base}/libraries/{library_id}/{version}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def publish(self, zip_content: bytes, **kwargs):
        form_data = FormData()
        form_data.add_field(
            "file", zip_content, filename="cdn.zip", content_type="identity"
        )

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                self.publish_url, data=form_data, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.publish_url, headers=self.headers
                )

    async def download_library(self, library_id: str, version: str, **kwargs):
        url = f"{self.download_url}/{library_id}/{version}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.read()
                await raise_exception_from_response(resp, url=url, headers=self.headers)

    async def publish_libraries(self, zip_path: Union[Path, str], **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            with open(zip_path, "rb") as fp:
                async with await session.post(
                    self.push_url, data={"file": fp}, **kwargs
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    await raise_exception_from_response(
                        resp, url=self.push_url, headers=self.headers
                    )

    async def delete_library(self, library_id: str, **kwargs):
        url = f"{self.url_base}/libraries/{library_id}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.push_url, headers=self.headers
                )

    async def delete_version(self, library_id: str, version: str, **kwargs):
        url = f"{self.url_base}/libraries/{library_id}/{version}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.push_url, headers=self.headers
                )

    async def get_explorer(
        self, library_id: str, version: str, folder_path: str, **kwargs
    ):
        url = f"{self.url_base}/explorer/{library_id}/{version}/{folder_path}"

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(
                    resp, url=self.push_url, headers=self.headers
                )

    async def get_entry_point(
        self,
        library_id: str,
        version: str,
        auto_decompress=True,
        reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        **kwargs,
    ):
        return await self.get_resource(
            library_id=library_id,
            version=version,
            rest_of_path="",
            reader=reader,
            auto_decompress=auto_decompress,
            **kwargs,
        )

    async def get_resource(
        self,
        library_id: str,
        version: str,
        rest_of_path: str,
        auto_decompress=True,
        reader: Callable[[ClientResponse], Awaitable[Any]] = None,
        **kwargs,
    ):
        url = (
            f"{self.url_base}/resources/{library_id}/{version}/{rest_of_path}"
            if rest_of_path
            else f"{self.url_base}/resources/{library_id}/{version}"
        )

        async with aiohttp.ClientSession(
            headers=self.headers, auto_decompress=auto_decompress
        ) as session:
            async with await session.get(url, **kwargs) as resp:
                if resp.status < 300:
                    return await extract_aiohttp_response(resp=resp, reader=reader)
                await raise_exception_from_response(
                    resp, url=self.push_url, headers=self.headers
                )
