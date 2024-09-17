# typing

# third parties
from pydantic import BaseModel


class PostFileResponse(BaseModel):
    """
    File information after creation.
    """

    fileId: str
    """
    File's ID.
    """
    fileName: str
    """
    File's name.
    """
    contentType: str
    """
    Content type.
    """
    contentEncoding: str
    """
    Content encoding.
    """


class Metadata(BaseModel):
    """
    File's metadata.
    """

    fileName: str
    """
    File's name.
    """
    contentType: str
    """
    Content type.
    """
    contentEncoding: str
    """
    Content encoding.
    """


class GetInfoResponse(BaseModel):
    """
    File info.
    """

    metadata: Metadata
    """
    File's metadata
    """


class PostMetadataBody(BaseModel):
    """
    Body to update file's metadata.
    """

    fileName: str | None = None
    """
    File's name.
    """
    contentType: str | None = None
    """
    Content type.
    """
    contentEncoding: str | None = None
    """
    Content encoding.
    """
