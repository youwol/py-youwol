# standard library
import itertools
import json as _json
import os
import shutil

from collections.abc import Mapping
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

# typing
from typing import Optional, Union, cast

# third parties
from fastapi import HTTPException

# Youwol utilities
from youwol.utils.clients.storage.models import FileData
from youwol.utils.clients.utils import get_default_owner
from youwol.utils.exceptions import ResourcesNotFoundException
from youwol.utils.types import JSON

flatten = itertools.chain.from_iterable


def create_dir_if_needed(full_path: Path):
    dir_path = full_path.parent
    if not dir_path.exists():
        os.makedirs(cast(PathLike, dir_path))


@dataclass(frozen=True)
class LocalStorageClient:
    root_path: Path
    bucket_name: str

    @property
    def bucket_path(self) -> Path:
        return self.root_path / self.bucket_name

    def get_full_path(self, owner: str, path: Union[str, Path]) -> Path:
        return self.bucket_path / owner[1:] / path

    async def delete_bucket(self, **_kwargs):
        if self.bucket_path.exists():
            shutil.rmtree(self.bucket_path)

    async def ensure_bucket(self, **_kwargs):
        if not self.bucket_path.exists():
            os.makedirs(cast(PathLike, self.bucket_path))

        return True

    async def post_file(
        self, form: FileData, headers: Optional[Mapping[str, str]] = None, **_kwargs
    ):
        if not headers:
            headers = {}
        full_path = self.get_full_path(
            form.owner if form.owner else get_default_owner(headers), form.objectName
        )

        create_dir_if_needed(full_path)
        full_path.open("wb").write(form.objectData)
        return {}

    async def post_object(
        self,
        path: Union[Path, str],
        content: bytes,
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}
        if isinstance(content, str):
            content = str.encode(content)

        data = content

        full_path = self.get_full_path(
            owner if owner else get_default_owner(headers), path
        )
        create_dir_if_needed(full_path)
        full_path.open("wb").write(data)

    async def post_json(
        self,
        path: Union[str, Path],
        json: JSON,
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        full_path = self.get_full_path(
            owner if owner else get_default_owner(headers), path
        )
        create_dir_if_needed(full_path)
        full_path.open("w").write(_json.dumps(json, indent=4))
        return {}

    async def post_text(
        self,
        path: Union[str, Path],
        text,
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        full_path = self.get_full_path(
            owner if owner else get_default_owner(headers), path
        )
        create_dir_if_needed(full_path)
        full_path.open("w").write(text)
        return {}

    async def delete_group(
        self,
        prefix: Union[Path, str],
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        path = self.get_full_path(
            owner if owner else get_default_owner(headers), prefix
        )
        if path.exists():
            shutil.rmtree(path)

    async def delete(
        self,
        path: Union[str, Path],
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        full_path = self.get_full_path(
            owner if owner else get_default_owner(headers), path
        )
        if full_path.is_dir():
            shutil.rmtree(full_path)
            return

        if not full_path.exists():
            raise HTTPException(
                status_code=404, detail=f"File {full_path.name} not found"
            )
        os.remove(full_path)

        return {}

    async def list_files(
        self,
        prefix: Union[str, Path],
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        path_owner = (owner if owner else get_default_owner(headers))[1:]
        results = [
            [(Path(root) / f).relative_to(self.bucket_path / path_owner) for f in files]
            for root, _, files in os.walk(self.bucket_path / path_owner / prefix)
        ]

        return [{"name": str(r)} for r in flatten(results)]

    async def get_bytes(
        self,
        path: Union[str, Path],
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **_kwargs,
    ):
        if not headers:
            headers = {}

        full_path = self.get_full_path(
            owner if owner else get_default_owner(headers), path
        )
        if not full_path.is_file():
            raise ResourcesNotFoundException(path=str(full_path))

        return full_path.open("rb").read()

    async def get_json(
        self,
        path: Union[str, Path],
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        return _json.loads(await self.get_bytes(path, owner, headers, **kwargs))

    async def get_text(
        self,
        path: str,
        owner: Optional[str],
        headers: Optional[Mapping[str, str]] = None,
        **kwargs,
    ):
        raw = await self.get_bytes(path, owner, headers, **kwargs)
        return raw.decode("utf-8")
