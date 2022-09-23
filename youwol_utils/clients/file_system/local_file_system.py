import io
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union, cast

from fastapi import HTTPException

from youwol_utils.clients.file_system.interfaces import FileSystemInterface
from youwol_utils.utils_paths import write_json, parse_json


def create_dir_if_needed(full_path: Path):
    dir_path = full_path.parent
    if not dir_path.exists():
        os.makedirs(cast(os.PathLike, dir_path))


@dataclass(frozen=True)
class LocalFileSystem(FileSystemInterface):

    root_path: Path

    def get_full_path(self, path: Union[str, Path]) -> Path:
        return self.root_path / path

    async def put_object(self, object_name: str, data: io.BytesIO, length: int = -1,
                         content_type: str = "", metadata: Dict[str, str] = None, **kwargs):

        metadata = metadata or {}
        path = self.get_full_path(object_name)
        create_dir_if_needed(path)
        content = data.read()
        path.open('wb').write(content)

        path_metadata = self.get_full_path(f"{object_name}.metadata.json")
        write_json(metadata, path_metadata)

    async def get_info(self, object_name: str, **kwargs):

        self.ensure_object_exist(object_name)
        path_metadata = self.get_full_path(f"{object_name}.metadata.json")
        if not path_metadata.exists():
            return {"metadata": {}}

        return {"metadata": parse_json(path_metadata)}

    async def set_metadata(self, object_name: str, metadata: Dict[str, str], **kwargs):

        self.ensure_object_exist(object_name)
        path_metadata = self.get_full_path(f"{object_name}.metadata.json")
        write_json(metadata, path_metadata)

    async def get_object(self, object_name: str, **kwargs):

        path = self.ensure_object_exist(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.get_object: Object '{path}' not found")

        return path.read_bytes()

    async def remove_object(self, object_name: str, **kwargs):

        path = self.ensure_object_exist(object_name)

        os.remove(path)
        path_metadata = self.get_full_path(f"{object_name}.metadata.json")
        if path_metadata.exists():
            os.remove(path_metadata)

    async def remove_folder(self, prefix: str, raise_not_found, **kwargs):
        path = self.get_full_path(prefix)
        if raise_not_found and not path.is_dir():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.remove_folder: Folder '{path}' not found")
        if not path.is_dir():
            return
        shutil.rmtree(path)

    def ensure_object_exist(self, object_name: str):
        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404,
                                detail=f"LocalFileSystem.ensure_object_exist: Object '{path}' not found")
        return path
