# standard library
import glob
import io
import os
import shutil

from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Union, cast

# third parties
from fastapi import HTTPException

# Youwol utilities
from youwol.utils.clients.file_system.interfaces import (
    FileObject,
    FileSystemInterface,
    Metadata,
)
from youwol.utils.utils_paths import parse_json, write_json


def create_dir_if_needed(full_path: Path):
    dir_path = full_path.parent
    if not dir_path.exists():
        os.makedirs(cast(os.PathLike, dir_path))


@dataclass(frozen=True)
class LocalFileSystem(FileSystemInterface):
    root_path: Path

    def get_full_path(self, path: Union[str, Path]) -> Path:
        return self.root_path / path

    async def ensure_bucket(self):
        #  Nothing to do here, the folder will be created on first object creation if needed
        pass

    async def put_object(
        self,
        object_id: str,
        data: io.BytesIO,
        object_name: str,
        content_type: str,
        content_encoding: str,
        **kwargs,
    ):
        path = self.get_full_path(object_id)
        create_dir_if_needed(path)
        content = data.read()
        path.open("wb").write(content)
        metadata = {
            "fileName": object_name,
            "contentType": content_type,
            "contentEncoding": content_encoding,
        }
        path_metadata = self.get_full_path(f"{object_id}.metadata.json")
        write_json(metadata, path_metadata)

    async def get_info(self, object_id: str, **kwargs):
        self.ensure_object_exist(object_id)
        path_metadata = self.get_full_path(f"{object_id}.metadata.json")
        if not path_metadata.exists():
            return {"metadata": {}}
        metadata = parse_json(path_metadata)
        return {"metadata": metadata}

    async def set_metadata(self, object_id: str, metadata: Metadata, **kwargs):
        info = await self.get_info(object_id=object_id)
        path_metadata = self.get_full_path(f"{object_id}.metadata.json")
        write_json(
            {**info["metadata"], **{k: v for k, v in metadata.dict().items() if v}},
            path_metadata,
        )

    async def get_object(
        self, object_id: str, ranges_bytes: [int, int] = None, **kwargs
    ):
        path = self.ensure_object_exist(object_id)
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"LocalFileSystem.get_object: Object '{path}' not found",
            )

        if not ranges_bytes:
            return path.read_bytes()
        acc = b""
        with open(path, "rb") as fp:
            for range_byte in ranges_bytes:
                fp.seek(range_byte[0], 0)
                acc += fp.read(range_byte[1] - range_byte[0] + 1)
        return acc

    async def remove_object(self, object_id: str, **kwargs):
        path = self.ensure_object_exist(object_id)

        os.remove(path)
        path_metadata = self.get_full_path(f"{object_id}.metadata.json")
        if path_metadata.exists():
            os.remove(path_metadata)

    async def remove_folder(self, prefix: str, raise_not_found, **kwargs):
        path = self.get_full_path(prefix)
        if raise_not_found and not path.is_dir():
            raise HTTPException(
                status_code=404,
                detail=f"LocalFileSystem.remove_folder: Folder '{path}' not found",
            )
        if not path.is_dir():
            return
        shutil.rmtree(path)

    def ensure_object_exist(self, object_id: str):
        path = self.get_full_path(object_id)
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"LocalFileSystem.ensure_object_exist: Object '{path}' not found",
            )
        return path

    async def list_objects(self, prefix: str, recursive: bool, **kwargs):
        base_path = self.root_path / prefix
        paths = [
            Path(p).relative_to(self.root_path)
            for p in glob.glob(
                pathname=str(base_path / "**" / "*"), recursive=recursive
            )
            if ".metadata.json" not in p and not Path(p).is_dir()
        ]
        return (
            FileObject(bucket_name=self.root_path.name, object_id=str(path))
            for path in paths
        )
