from typing import Union

from pydantic import BaseModel


class GetRawResp(BaseModel):
    rawId: str
    content: Union[str, bytes]


class PostDataBody(BaseModel):
    folderId: str
    fileName: str
    content: str


class PostDataResp(BaseModel):
    assetId: str
    rawId: str
    treeId: str
