# typing
from typing import Optional

# third parties
from pydantic import BaseModel


class PostFileResponse(BaseModel):
    fileId: str
    fileName: str
    contentType: str
    contentEncoding: str


class Metadata(BaseModel):
    fileName: str
    contentType: str
    contentEncoding: str


class GetInfoResponse(BaseModel):
    metadata: Metadata


class PostMetadataBody(BaseModel):
    fileName: Optional[str] = None
    contentType: Optional[str] = None
    contentEncoding: Optional[str] = None
