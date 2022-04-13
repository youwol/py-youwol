import io
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, cast, Union

from fastapi import HTTPException

from youwol_utils import create_dir_if_needed


@dataclass(frozen=True)
class MockMinioPersistentClient:

    root_path: Path
    bucket_name: str

    @property
    def base_path(self):
        return Path(self.root_path) / self.bucket_name / 'youwol-users'

    @property
    def bucket_path(self) -> Path:
        return self.root_path / self.bucket_name

    def get_full_path(self, path: Union[str, Path]) -> Path:
        return self.bucket_path / 'youwol-users' / path

    async def delete_bucket(self, **_kwargs):
        if self.bucket_path.exists():
            shutil.rmtree(self.bucket_path)

    async def ensure_bucket(self, **_kwargs):
        if not self.bucket_path.exists():
            os.makedirs(cast(os.PathLike, self.bucket_path))

        return True

    def put_object(self, object_name: str, data: io.BytesIO, length: int = -1,
                   content_type: str = "", metadata: Dict[str, str] = None):

        metadata = metadata or {}
        path = self.get_full_path(object_name)
        create_dir_if_needed(path)
        content = data.read()
        path.open('wb').write(content)
        for key, value in metadata.items():
            os.setxattr(path, f'user.{key}', value.encode('utf8'))

    def get_stats(self, object_name: str):

        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"MockMinioPersistentClient.get_stats: Object '{path}' "
                                                        f"not found")

        metadata = {}
        for key in ['contentType', 'contentEncoding', 'fileName', 'fileId']:
            metadata[key] = os.getxattr(path, f'user.{key}').decode('utf8')

        return {"metadata": metadata}

    def set_metadata(self, object_name: str, metadata: Dict[str, str]):

        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"MockMinioPersistentClient.set_metadata: Object '{path}'"
                                                        f" not found")

        for key, value in metadata.items():
            os.setxattr(path, f'user.{key}', value.encode('utf8'))

    def get_object(self, object_name: str):
        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"MockMinioPersistentClient.get_object: Object '{path}' "
                                                        f"not found")

        return path.read_bytes()

    def remove_object(self, object_name: str):
        path = self.get_full_path(object_name)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"MockMinioPersistentClient.remove_object: Object '{path}'"
                                                        f" not found")

        os.remove(path)
