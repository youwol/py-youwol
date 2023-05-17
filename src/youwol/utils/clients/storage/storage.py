# standard library
import base64
import json as _json

from dataclasses import dataclass, field
from pathlib import Path

# typing
from typing import Dict, Union

# third parties
import aiohttp

from aiohttp import FormData

# Youwol utilities
from youwol.utils.clients.storage.models import FileData
from youwol.utils.clients.storage.patches import patch_files_name
from youwol.utils.exceptions import raise_exception_from_response
from youwol.utils.types import JSON


def post_drive_body(name: str):
    return {"name": name, "region": "NoCloudProvider"}


@dataclass(frozen=True)
class StorageClient:
    bucket_name: str

    url_base: str

    version: str = "v0-alpha1"

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    @property
    def create_bucket_url(self):
        return f"{self.url_base}/{self.version}/bucket"

    @property
    def list_buckets_url(self):
        return f"{self.url_base}/{self.version}/buckets"

    @property
    def delete_bucket_url(self):
        return f"{self.url_base}/{self.version}/bucket/{self.bucket_name}"

    @property
    def object_url(self):
        return f"{self.url_base}/{self.version}/{self.bucket_name}/object"

    @property
    def objects_url(self):
        return f"{self.url_base}/{self.version}/{self.bucket_name}/objects"

    @property
    def upload_file_url(self):
        return f"{self.url_base}/{self.version}/{self.bucket_name}/file"

    @property
    def upload_file_url_v0(self):
        return f"{self.url_base}/v0/{self.bucket_name}/file"

    @property
    def list_files_url(self):
        return f"{self.url_base}/{self.version}/{self.bucket_name}/objects"

    async def delete_bucket(self, force_not_empty=False, **kwargs):
        bucket_list = await self.list_buckets()
        if self.bucket_name not in [b["name"] for b in bucket_list]:
            return

        url = (
            self.delete_bucket_url + "?forceNotEmpty=true"
            if force_not_empty
            else self.delete_bucket_url
        )
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=url, **kwargs) as resp:
                if resp.status == 200:
                    print("Bucket deleted", self.bucket_name)
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def list_buckets(self, **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.list_buckets_url, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def ensure_bucket(self, **kwargs):
        buckets = await self.list_buckets(**kwargs)
        if self.bucket_name in [b["name"] for b in buckets]:
            print(f"bucket {self.bucket_name} exists")
            return True
        body = post_drive_body(self.bucket_name)
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.create_bucket_url, json=body, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"bucket '{self.bucket_name}' created")
                    return True
                await raise_exception_from_response(resp)
        return False

    async def post_file(self, form: FileData, **kwargs):
        data = FormData()
        data.add_field("objectName", str(form.objectName))
        data.add_field("objectData", form.objectData)
        data.add_field("objectSize", str(form.objectSize))
        data.add_field("contentType", form.content_type)
        data.add_field("contentEncoding", form.content_encoding)
        if form.owner:
            data.add_field("owner", form.owner)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.upload_file_url, data=data, **kwargs
            ) as resp:
                if resp.status == 201:
                    return await resp.read()
                await raise_exception_from_response(resp)

    async def post_object(
        self,
        path: Union[Path, str],
        content: Union[str, bytes],
        content_type: str,
        owner: Union[str, None],
        **kwargs,
    ):
        if isinstance(content, str):
            content = str.encode(content)
        data = base64.b64encode(content)

        body = {
            "object": {
                "name": str(path),
                "data": data.decode("utf-8"),
                "size": len(content),
            },
            "options": {"content-type": content_type},
        }
        params = {"owner": owner} if owner else {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.object_url, json=body, params=params, **kwargs
            ) as resp:
                if resp.status == 201:
                    return await resp.read()
                await raise_exception_from_response(resp)

    async def post_json(self, path: Union[Path, str], json: JSON, owner: str, **kwargs):
        str_json = _json.dumps(json)
        return await self.post_object(
            path,
            content=str_json,
            content_type="application/json",
            owner=owner,
            **kwargs,
        )

    async def post_text(self, path: Union[Path, str], text: str, owner: str, **kwargs):
        return await self.post_object(
            path, content=text, content_type="text/html", owner=owner, **kwargs
        )

    async def delete_group(
        self, prefix: Union[Path, str], owner: Union[str, None], **kwargs
    ):
        params = {"prefix": str(prefix), "recursive": "true"}
        if owner:
            params["owner"] = owner

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(
                url=self.objects_url, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def delete(self, path: Union[Path, str], owner: Union[str, None], **kwargs):
        params = {"objectName": str(path)}
        if owner:
            params["owner"] = owner

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(
                url=self.object_url, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await raise_exception_from_response(resp)

    async def list_files(
        self,
        prefix: Union[Path, str],
        owner: Union[str, None],
        _max_results: int = 1e6,
        _delimiter=None,
        **kwargs,
    ):
        params = {"prefix": str(prefix), "recursive": "true"}
        if owner:
            params["owner"] = owner

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(
                url=self.list_files_url, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    files = await resp.json()
                    return patch_files_name(files)
                await raise_exception_from_response(resp)

    async def get_bytes(
        self, path: Union[Path, str], owner: Union[str, None], **kwargs
    ):
        url = self.object_url
        params = {"objectName": str(path)}
        if owner:
            params["owner"] = owner

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=url, params=params, **kwargs) as resp:
                if resp.status == 200:
                    resp_bytes = await resp.read()
                    return base64.decodebytes(resp_bytes)
                await raise_exception_from_response(resp)

    async def get_json(self, path: Union[Path, str], owner: Union[str, None], **kwargs):
        content = await self.get_bytes(path, owner, **kwargs)
        return _json.loads(content.decode("utf-8"))

    async def get_text(self, path: Union[Path, str], owner: Union[str, None], **kwargs):
        content = await self.get_bytes(path, owner, **kwargs)
        return content.decode("utf-8")
