# standard library
import base64

# third parties
from pydantic import BaseModel, validator

methods = ["GET", "POST", "PUT", "DELETE"]


class Body(BaseModel):
    mimeType: str | None
    contentBase64: str


class Status(BaseModel):
    code: int
    string: str


status_200_OK = Status(code=200, string="OK")
status_204_NoContent = Status(code=204, string="No Content")


class Response(BaseModel):
    status: Status = status_200_OK
    headers: dict[str, list[str]] = {}
    body: Body = Body(
        mimeType="application/json",
        contentBase64=base64.b64encode(b'{"status":"ok"}').decode(),
    )


class Request(BaseModel):
    timestamp: int
    ip: str | None
    method: str
    url: str
    headers: dict[str, list[str]]
    body: Body | None
    auth: str | None


class Handler(BaseModel):
    method: str = "GET"
    response: Response = Response()
    historyCapacity: int = 10
    history: list[Request] | None = None

    @classmethod
    @validator("history")
    def history_is_some(cls, v: list[Request] | None) -> list[Request]:
        if v is None:
            raise ValueError("If provided history must be a list")
        return v

    @classmethod
    @validator("historyCapacity")
    def history_capacity_strictly_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("If provided historyCapacity must be strictly positive")
        return v
