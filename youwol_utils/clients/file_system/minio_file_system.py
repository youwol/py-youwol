import io
from dataclasses import dataclass

from typing import Dict
from minio import Minio, S3Error
from minio.commonconfig import REPLACE, CopySource

from youwol_utils import ResourcesNotFoundException, ServerError
from youwol_utils.clients.file_system.interfaces import FileSystemInterface


@dataclass(frozen=True)
class MinioFileSystem(FileSystemInterface):

    client: Minio
    bucket_name: str

    metadata_keys = {
        'x-amz-meta-contentencoding': 'contentEncoding',
        'x-amz-meta-contenttype': 'contentType',
        'x-amz-meta-filename': 'fileName'
    }

    async def ensure_bucket(self):
        buckets = self.client.list_buckets()
        if self.bucket_name not in [b.name for b in buckets]:
            self.client.make_bucket(self.bucket_name)

    async def list_buckets(self):
        try:
            return self.client.list_buckets()
        except S3Error as e:
            raise ServerError(
                status_code=500,
                detail=f"MinioFileSystem.list_buckets: {e.message}"
            )

    async def put_object(self, object_name: str, data: io.BytesIO, length: int = -1,
                         content_type: str = "", metadata: Dict[str, str] = None):
        try:
            length = data.getbuffer().nbytes if length == -1 else length
            return self.client.put_object(
                self.bucket_name, object_name=object_name, data=data, length=length,
                metadata=metadata, content_type=content_type
            )
        except S3Error as e:
            raise ServerError(
                status_code=500,
                detail=f"MinioFileSystem.put_object: {e.message}"
            )

    async def get_info(self, object_name: str, **kwargs):

        try:
            stat = self.client.stat_object(
                self.bucket_name, object_name=object_name
            )
            return {
                "metadata": {v: stat.metadata[k] for k, v in self.metadata_keys.items()}
                }
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_name}",
                detail=f"MinioFileSystem.get_stats: {e.message}"
            )

    async def set_metadata(self, object_name: str, metadata: Dict[str, str], **kwargs):

        try:
            response = self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                source=CopySource(self.bucket_name, object_name),
                metadata=metadata,
                metadata_directive=REPLACE,
            )
            return response
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_name}",
                detail=f"MinioFileSystem.set_metadata: {e.message}")

    async def get_object(self, object_name: str, **kwargs):

        try:
            response = self.client.get_object(bucket_name=self.bucket_name, object_name=object_name)
            return response.read()
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_name}",
                detail=f"MinioFileSystem.get_object: {e.message}"
            )

    async def remove_object(self, object_name: str, **kwargs):
        try:
            response = self.client.remove_object(bucket_name=self.bucket_name, object_name=object_name)
            return response
        except S3Error as e:
            raise ServerError(
                status_code=500,
                detail=f"MinioFileSystem.remove_object: {e.message}"
            )

