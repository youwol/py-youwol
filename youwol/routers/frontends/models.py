from typing import List, Union

from pydantic import BaseModel


class InfoFront(BaseModel):
    pass


class StatusResponse(BaseModel):
    name: str
    url: str
    health: bool
    devServer: Union[bool, None]


class AllStatusResponse(BaseModel):
    status: List[StatusResponse]
