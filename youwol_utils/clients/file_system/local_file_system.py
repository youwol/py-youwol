import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union

from fastapi import HTTPException

from youwol_utils import create_dir_if_needed
from youwol_utils.clients.file_system.interfaces import FileSystemInterface


@dataclass(frozen=True)
class LocalFileSystem(FileSystemInterface):

    root_path: Path

    def get_full_path(self, path: Union[str, Path]) -> Path:
        return self.root_path / path

    async def put_object(self, object_name: str, data: io.BytesIO, length: int = -1,
                   content_type: str = "", metadata: Dict[str, str] = None):

        metadata = metadata or {}
        path = self.get_full_path(object_name)
        create_dir_if_needed(path)
        content = data.read()
        path.open('wb').write(content)
        for key, value in metadata.items():
            os.setxattr(path, f'user.{key}', value.encode('utf8'))

    async def get_info(self, object_name: str, **kwargs):

        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.get_stats: Object '{path}' "
                                                        f"not found")

        metadata = {}
        for key in ['contentType', 'contentEncoding', 'fileName', 'fileId']:
            metadata[key] = os.getxattr(path, f'user.{key}').decode('utf8')

        return {"metadata": metadata}

    async def set_metadata(self, object_name: str, metadata: Dict[str, str], **kwargs):

        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.set_metadata: Object '{path}'"
                                                        f" not found")

        for key, value in metadata.items():
            os.setxattr(path, f'user.{key}', value.encode('utf8'))

    async def get_object(self, object_name: str, **kwargs):
        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.get_object: Object '{path}' "
                                                        f"not found")

        return path.read_bytes()

    async def remove_object(self, object_name: str, **kwargs):
        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"LocalFileSystem.remove_object: Object '{path}'"
                                                        f" not found")

        os.remove(path)
