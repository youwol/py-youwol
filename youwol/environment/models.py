from typing import List, Dict

from pydantic import BaseModel


class UserInfo(BaseModel):
    id: str
    name: str
    email: str
    memberOf: List[str]


class RemoteGateway(BaseModel):
    name: str
    host: str
    metadata: Dict[str, str]


class Secret(BaseModel):
    clientId: str
    clientSecret: str
