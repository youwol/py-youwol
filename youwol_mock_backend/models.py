from pydantic import BaseModel
from typing import Dict, List, Optional

methods = ["GET", "POST", "PUT", "DELETE"]


class Body(BaseModel):
    mimeType: str
    contentBase64: str


class Status(BaseModel):
    code: int
    string: str


status_200_OK = Status(code=200, string="OK")
status_204_NoContent = Status(code=204, string="No Content")


class Response(BaseModel):
    status: Status = status_200_OK
    headers: Dict[str, List[str]] = dict()
    body: Body = Body(mimeType="application/json", contentBase64="eyJzdGF0dXMiOiJvayJ9")


class Request(BaseModel):
    timestamp: int
    ip: str
    method: str
    url: str
    headers: Dict[str, List[str]]
    body: Optional[Body]


class Handler(BaseModel):
    method: str = "GET"
    response: Response = Response()
    historySize: int = 10
    history: List[Request] = []
