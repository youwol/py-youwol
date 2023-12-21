# standard library
import functools
import hashlib

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Optional, Union

# third parties
from aiohttp import FormData

# Youwol utilities
from youwol.utils.clients.request_executor import (
    RequestExecutor,
    auto_reader,
    bytes_reader,
    json_reader,
)
from youwol.utils.types import JSON


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
    return sha_hash.hexdigest()


@dataclass(frozen=True)
class CdnClient:
    """
    HTTP client of the [cdn](@yw-nav-mod:youwol.backends.cdn) service.
    """

    url_base: str
    """
    Base URL used for the request.
    """

    request_executor: RequestExecutor
    """
    Request executor.
    """

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

    async def query_packs(self, namespace: Optional[str] = None, **kwargs):
        url = (
            self.packs_url
            if not namespace
            else f"{self.packs_url}?namespace={namespace}"
        )
        return await self.request_executor.get(
            url=url,
            default_reader=json_reader,
            **kwargs,
        )

    async def query_libraries(self, **kwargs):
        return await self.request_executor.get(
            url=self.libraries_url,
            default_reader=json_reader,
            **kwargs,
        )

    async def query_dependencies_latest(self, libraries: list[str], **kwargs):
        return await self.request_executor.post(
            url=self.dependencies_url,
            default_reader=json_reader,
            json={"libraries": libraries},
            **kwargs,
        )

    async def query_loading_graph(self, body: JSON, **kwargs):
        """
        See description in
        [cdn.resolve_loading_tree](@yw-nav-func:youwol.backends.cdn.root_paths.resolve_loading_tree).
        """
        return await self.request_executor.post(
            url=self.loading_graph_url,
            default_reader=json_reader,
            json=body,
            **kwargs,
        )

    async def get_json(self, url: Union[Path, str], **kwargs):
        return await self.request_executor.get(
            url=f"{self.url_base}/{str(url)}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_library_info(
        self,
        library_id: str,
        semver: Optional[str] = None,
        max_count: Optional[int] = None,
        **kwargs,
    ):
        """
        See description in
        [cdn.get_library_info](@yw-nav-func:youwol.backends.cdn.root_paths.get_library_info).
        """
        query_params = [
            (k, v)
            for k, v in {"semver": semver, "max-count": max_count}.items()
            if v is not None
        ]
        suffix = functools.reduce(
            lambda acc, item: acc + f"{acc}{item[0]}={item[1]}&", query_params, ""
        )

        url = f"{self.url_base}/libraries/{library_id}?{suffix}"
        return await self.request_executor.get(
            url=url,
            default_reader=json_reader,
            **kwargs,
        )

    async def get_version_info(self, library_id: str, version: str, **kwargs):
        """
        See description in
        [cdn.get_version_info](@yw-nav-func:youwol.backends.cdn.root_paths.get_version_info).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/libraries/{library_id}/{version}",
            default_reader=json_reader,
            **kwargs,
        )

    async def publish(self, zip_content: bytes, **kwargs):
        """
        See description in
        [cdn.publish_library](@yw-nav-func:youwol.backends.cdn.root_paths.publish_library).
        """
        form_data = FormData()
        form_data.add_field(
            "file", zip_content, filename="cdn.zip", content_type="identity"
        )
        return await self.request_executor.post(
            url=self.publish_url,
            data=form_data,
            default_reader=json_reader,
            **kwargs,
        )

    async def download_library(self, library_id: str, version: str, **kwargs):
        """
        See description in
        [cdn.download_library](@yw-nav-func:youwol.backends.cdn.root_paths.download_library).
        """
        return await self.request_executor.get(
            url=f"{self.download_url}/{library_id}/{version}",
            default_reader=bytes_reader,
            **kwargs,
        )

    async def publish_libraries(self, zip_path: Union[Path, str], **kwargs):
        with open(zip_path, "rb") as fp:
            return await self.request_executor.post(
                url=self.push_url,
                data={"file": fp},
                default_reader=json_reader,
                **kwargs,
            )

    async def delete_library(self, library_id: str, **kwargs):
        """
        See description in
        [cdn.delete_library](@yw-nav-func:youwol.backends.cdn.root_paths.delete_library).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/libraries/{library_id}",
            default_reader=json_reader,
            **kwargs,
        )

    async def delete_version(self, library_id: str, version: str, **kwargs):
        """
        See description in
        [cdn.delete_version](@yw-nav-func:youwol.backends.cdn.root_paths.delete_version).
        """
        return await self.request_executor.delete(
            url=f"{self.url_base}/libraries/{library_id}/{version}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_explorer(
        self, library_id: str, version: str, folder_path: str, **kwargs
    ):
        """
        See description in
        [cdn.explorer](@yw-nav-func:youwol.backends.cdn.root_paths.explorer).
        """
        return await self.request_executor.get(
            url=f"{self.url_base}/explorer/{library_id}/{version}/{folder_path}",
            default_reader=json_reader,
            **kwargs,
        )

    async def get_entry_point(
        self,
        library_id: str,
        version: str,
        **kwargs,
    ):
        """
        See description in
        [cdn.get_entry_point](@yw-nav-func:youwol.backends.cdn.root_paths.get_entry_point).
        """
        return await self.get_resource(
            library_id=library_id,
            version=version,
            rest_of_path="",
            **kwargs,
        )

    async def get_resource(
        self,
        library_id: str,
        version: str,
        rest_of_path: str,
        **kwargs,
    ):
        """
        See description in
        [cdn.get_resource](@yw-nav-func:youwol.backends.cdn.root_paths.get_resource).
        """
        url = (
            f"{self.url_base}/resources/{library_id}/{version}/{rest_of_path}"
            if rest_of_path
            else f"{self.url_base}/resources/{library_id}/{version}"
        )

        return await self.request_executor.get(
            url=url,
            default_reader=auto_reader,
            **kwargs,
        )
