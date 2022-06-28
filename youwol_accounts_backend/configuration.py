from typing import Union, Optional, Callable, Awaitable

from pydantic import BaseModel

from youwol_utils.clients.oidc.oidc_config import PrivateClient, PublicClient


class Configuration(BaseModel):
    openid_base_url: str
    openid_client: Union[PrivateClient,PublicClient]
    keycloak_admin_base_url: Optional[str]
    admin_client: Optional[PrivateClient]


class Dependencies:
    get_configuration: Callable[[], Union[Configuration, Awaitable[Configuration]]]


async def get_configuration():
    conf = Dependencies.get_configuration()

    if isinstance(conf, Configuration):
        return conf
    else:
        return await conf
