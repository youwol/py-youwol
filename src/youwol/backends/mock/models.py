# typing
from typing import Optional

# third parties
from pydantic import BaseModel

methods = ["GET", "POST", "PUT", "DELETE"]


class Body(BaseModel):
    mimeType: Optional[str]
    contentBase64: str


class Status(BaseModel):
    code: int
    string: str


status_200_OK = Status(code=200, string="OK")
status_204_NoContent = Status(code=204, string="No Content")


class Response(BaseModel):
    status: Status = status_200_OK
    headers: dict[str, list[str]] = {}
    body: Body = Body(mimeType="application/json", contentBase64="eyJzdGF0dXMiOiJvayJ9")


class Request(BaseModel):
    timestamp: int
    ip: Optional[str]
    method: str
    url: str
    headers: dict[str, list[str]]
    body: Optional[Body]


class Handler(BaseModel):
    method: str = "GET"
    response: Response = Response()
    historySize: int = 10
    history: list[Request] = []
