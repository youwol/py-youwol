from enum import Enum
from typing import List, NamedTuple, Union

from pydantic import BaseModel


class InstallStatus(Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    INSTALLED = "INSTALLED"


class TargetStatus(NamedTuple):

    install_status: InstallStatus


class StatusResponse(BaseModel):
    assetId: str
    name: str
    url: str
    health: bool
    openApi: Union[str, None]
    devServer: bool
    installStatus: str


class AllStatusResponse(BaseModel):
    status: List[StatusResponse]
