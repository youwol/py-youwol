# standard library
import io

from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Optional, Union

# third parties
from minio import Minio, S3Error
from minio.commonconfig import REPLACE, CopySource
from minio.deleteobjects import DeleteObject

# Youwol utilities
from youwol.utils.clients.file_system.interfaces import (
    FileObject,
    FileSystemInterface,
    Metadata,
)
from youwol.utils.exceptions import ResourcesNotFoundException, ServerError


@dataclass(frozen=True)
class MinioFileSystem(FileSystemInterface):
    """
    Implementation of storage for remote usage (connected to a [Minio](https://min.io/ S3 service).
    client.
    """

    client: Minio
    """
    Minio client
    """
    bucket_name: str
    """
    Bucket name
    """
    root_path: Union[str, Path] = ""
    """
    Reference path (in the bucket) of all operations in this class.
    """

    metadata_keys = {
        "x-amz-meta-contentencoding": "contentEncoding",
        "x-amz-meta-contenttype": "contentType",
        "x-amz-meta-filename": "fileName",
    }

    async def ensure_bucket(self):
        if not self.client.bucket_exists(bucket_name=self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    async def list_buckets(self):
        try:
            return self.client.list_buckets()
        except S3Error as e:
            raise ServerError(
                status_code=500, detail=f"MinioFileSystem.list_buckets: {e.message}"
            )

    async def put_object(
        self,
        object_id: str,
        data: io.BytesIO,
        object_name: str,
        content_type: str,
        content_encoding: str,
        length=-1,
        **kwargs,
    ):
        object_path = self.get_object_path(object_id)
        metadata = {
            "fileName": object_name,
            "contentType": content_type,
            "contentEncoding": content_encoding,
        }

        try:
            length = data.getbuffer().nbytes if length == -1 else length
            return self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                data=data,
                length=length,
                metadata=metadata,
                content_type=content_type,
            )
        except S3Error as e:
            raise ServerError(
                status_code=500, detail=f"MinioFileSystem.put_object: {e.message}"
            )

    async def get_info(self, object_id: str, **kwargs):
        object_id = self.get_object_path(object_id)
        try:
            stat = self.client.stat_object(self.bucket_name, object_name=object_id)
            return {
                "metadata": {
                    v: stat.metadata[k]
                    for k, v in self.metadata_keys.items()
                    if k in stat.metadata
                }
            }
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_id}",
                detail=f"MinioFileSystem.get_stats: {e.message}",
            )

    async def set_metadata(self, object_id: str, metadata: Metadata, **kwargs):
        object_id = self.get_object_path(object_id)
        try:
            info = await self.get_info(object_id=object_id)

            response = self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=object_id,
                source=CopySource(self.bucket_name, object_id),
                metadata={
                    **info["metadata"],
                    **{k: v for k, v in metadata.dict().items() if v},
                },
                metadata_directive=REPLACE,
            )
            return response
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_id}",
                detail=f"MinioFileSystem.set_metadata: {e.message}",
            )

    async def get_object(
        self,
        object_id: str,
        ranges_bytes: Optional[list[tuple[int, int]]] = None,
        **kwargs,
    ):
        object_id = self.get_object_path(object_id)
        if ranges_bytes and len(ranges_bytes) > 1:
            raise RuntimeError(
                "Minio file system does not support multiple ranges bytes"
            )

        try:
            if ranges_bytes:
                first_range = ranges_bytes[0]
                response = self.client.get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_id,
                    offset=first_range[0],
                    length=first_range[1] - first_range[0] + 1,
                )
                return response.read()

            response = self.client.get_object(
                bucket_name=self.bucket_name, object_name=object_id
            )
            return response.read()
        except S3Error as e:
            raise ResourcesNotFoundException(
                path=f"{self.bucket_name}:{object_id}",
                detail=f"MinioFileSystem.get_object: {e.message}",
            )

    async def remove_object(self, object_id: str, **kwargs):
        object_id = self.get_object_path(object_id)
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name, object_name=object_id
            )
        except S3Error as e:
            raise ServerError(
                status_code=500, detail=f"MinioFileSystem.remove_object: {e.message}"
            )

    async def remove_folder(self, prefix: str, raise_not_found: bool, **kwargs):
        prefix = self.get_object_path(prefix)
        try:
            delete_object_list = map(
                lambda x: DeleteObject(x.object_name),
                self.client.list_objects(
                    bucket_name=self.bucket_name, prefix=prefix, recursive=True
                ),
            )
            if raise_not_found and not delete_object_list:
                raise ResourcesNotFoundException(
                    path=f"{self.bucket_name}:{prefix}",
                    detail="MinioFileSystem.remove_folder",
                )

            response = self.client.remove_objects(
                bucket_name=self.bucket_name, delete_object_list=delete_object_list
            )
            return response
        except S3Error as e:
            raise ServerError(
                status_code=500, detail=f"MinioFileSystem.remove_folder: {e.message}"
            )

    def get_object_path(self, object_id: str):
        return f"{str(self.root_path).strip('/')}/{object_id}"

    async def list_objects(self, prefix: str, recursive: bool, **kwargs):
        return (
            FileObject(bucket_name=o.bucket_name, object_id=o.object_name)
            for o in self.client.list_objects(
                bucket_name=self.bucket_name, prefix=prefix, recursive=recursive
            )
        )
