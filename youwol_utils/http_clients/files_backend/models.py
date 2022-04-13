from typing import Optional

from pydantic import BaseModel


class PostFileResponse(BaseModel):
    fileId: str
    fileName: str
    contentType: str
    contentEncoding: str


class Metadata(PostFileResponse):
    pass


class GetStatsResponse(BaseModel):
    metadata: Metadata


class PostMetadataBody(BaseModel):
    fileName: Optional[str] = None
    contentType: Optional[str] = None
    contentEncoding: Optional[str] = None
