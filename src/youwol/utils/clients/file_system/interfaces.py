# standard library
import io

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

# typing
from typing import Optional

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.types import AnyDict


@dataclass(frozen=True)
class FileObject:
    """
    Subset of Minio's Object class used in youwol
    """

    bucket_name: str
    """
    Bucket name.
    """
    object_id: str
    """
    Object ID.
    """


class Metadata(BaseModel):
    """
    Metadata of a file w/
    [FileSystemInterface](@yw-nav-class:youwol.utils.clients.file_system.interfaces.FileSystemInterface).
    """

    fileName: Optional[str]
    """
    Filename.
    """

    contentType: Optional[str]
    """
    Content type.
    """

    contentEncoding: Optional[str]
    """
    Content encoding.
    """


class FileSystemInterface(ABC):
    """
    Abstract class defining methods for interacting with a file system.

    It is bound to a concept a bucket: all methods defined here referred to it.
    """

    @abstractmethod
    async def ensure_bucket(self):
        """
        Ensure the existence of the file storage bucket.
        """
        raise NotImplementedError

    @abstractmethod
    async def put_object(
        self,
        object_id: str,
        data: io.BytesIO,
        object_name: str,
        content_type: str,
        content_encoding: str,
        **kwargs: AnyDict,
    ) -> None:
        """
        Upload an object to the file storage.

        Parameters:
            object_id: UID of the object
            data: Content of the object
            object_name: name of the object
            content_type: MIME type of the content,
            content_encoding: Encoding of the content.
            kwargs: Additional keyword arguments.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_info(self, object_id: str, **kwargs: AnyDict) -> AnyDict:
        """
        Retrieve information about a specific object.

        Parameters:
            object_id: Unique identifier for the object.
            kwargs: Additional keyword arguments.
        Return:
            Metadata and information about the object.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_metadata(
        self, object_id: str, metadata: Metadata, **kwargs: AnyDict
    ) -> None:
        """
        Set metadata for a specified object.

        Parameters:
            object_id: Unique identifier for the object.
            metadata: metadata definition
            kwargs: Additional keyword arguments.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_object(
        self,
        object_id: str,
        ranges_bytes: Optional[list[tuple[int, int]]] = None,
        **kwargs: AnyDict,
    ) -> bytes:
        """
        Retrieve the content of a specific object.

        Parameters:
            object_id: Unique identifier for the object.
            ranges_bytes: List of byte ranges to retrieve.

                Warning:
                    Only one range is supported.
            kwargs: Additional keyword arguments.

        Return:
            Content of the object and metadata.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_object(self, object_id: str, **kwargs: AnyDict) -> None:
        """
        Remove a specific object from the file storage.

        Parameters:
            object_id: Unique identifier for the object.
            kwargs: Additional keyword arguments.
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_folder(
        self, prefix: str, raise_not_found: bool, **kwargs: AnyDict
    ) -> None:
        """
        Remove all objects under a prefix.

        Parameters:
            prefix: Prefix of the objects to remove.
            raise_not_found: If true, an exception is raised if not objects includes this prefix.
            kwargs: Additional keyword arguments.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_objects(
        self, prefix: str, recursive: bool, **kwargs: AnyDict
    ) -> Iterable[FileObject]:
        """
        List objects under a provided prefix.

        Parameters:
            prefix: Prefix of the objects to remove.
            recursive: If true, do a recursive lookup.
            kwargs: Additional keyword arguments.

        Return:
            Iterable over the objects.
        """
        raise NotImplementedError
