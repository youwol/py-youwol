# standard library
import re

from contextlib import asynccontextmanager

# typing
from typing import Dict, Optional

# third parties
import aiohttp

from fastapi import FastAPI
from prometheus_client import Counter
from pydantic import BaseModel
from pydantic.dataclasses import dataclass

# Youwol utilities
from youwol.utils import CleanerThread, OidcConfig, PrivateClient, factory_local_cache
from youwol.utils.clients.oidc.tokens_manager import SessionLessTokenManager


class ConfigurationOrigin(BaseModel):
    secure: bool
    hostname: str
    port: int


def config_origin_from_host(host: str):
    secure = False
    if host.startswith("https://"):
        secure = True
    elif not host.startswith("http://"):
        raise RuntimeError(f"Host '{host}' does not start with scheme")
    after_scheme_pos = 8 if secure else 7
    host_without_scheme = host[after_scheme_pos:]
    colon_pos = host_without_scheme.find(":")
    if colon_pos != -1:
        port = host_without_scheme[colon_pos + 1 :]
        if str(int(port)) != port:
            raise RuntimeError(f"Host '{host}' has invalid port {port}")
    else:
        port = 443 if secure else 80
        colon_pos = len(host_without_scheme)
    hostname = host_without_scheme[:colon_pos]
    return ConfigurationOrigin(secure=secure, hostname=hostname, port=port)


@dataclass(frozen=True)
class Configuration:
    version: str
    oidc_issuer: str
    client_id: str
    client_secret: str
    assets_gateway_base_url: str
    config_id: str
    origin: ConfigurationOrigin
    default_cdn_client_version: str


class ConfigurationFactory:
    __configuration: Optional[Configuration]

    @classmethod
    def get(cls) -> Configuration:
        return cls.__configuration

    @classmethod
    def set(cls, **kwargs):
        cls.__configuration = Configuration(**kwargs)


class Dependencies:
    def __init__(self, configuration: Configuration):
        self.__cleaner_thread = CleanerThread()
        self.__cleaner_thread.go()
        cache = factory_local_cache(self.__cleaner_thread, "auth_cache")
        session_less_token_manager = SessionLessTokenManager(
            cache=cache,
            oidc_client=OidcConfig(base_url=configuration.oidc_issuer).for_client(
                client=PrivateClient(
                    client_id=configuration.client_id,
                    client_secret=configuration.client_secret,
                )
            ),
            cache_key="sa_webpm_token",
        )
        self.session_less_token_manager = session_less_token_manager
        self.client_session = aiohttp.ClientSession(auto_decompress=False)
        self.configuration = configuration

    async def shutdown(self):
        await self.client_session.close()
        self.__cleaner_thread.join(3)


class CountVersions:
    def __init__(self):
        self.__counters: Dict[str, Counter] = {}

    def inc(self, version: str):
        version_safe = re.sub(r"[^[a-zA-Z0-9_]", r"_", version)
        if version_safe not in self.__counters:
            self.__counters[version_safe] = Counter(
                f"webpm_cdn_client_js_{version_safe}",
                f"Nb of cdn-client.js of version {version} download",
            )
        self.__counters[version_safe].inc()


class DependenciesFactory:
    __dependencies: Optional[Dependencies] = None

    def __call__(self) -> Dependencies:
        if self.__dependencies is None:
            raise RuntimeError("Dependencies not build")
        return self.__dependencies

    @classmethod
    async def build(cls):
        if cls.__dependencies is not None:
            await cls.__dependencies.shutdown()
        cls.__dependencies = Dependencies(configuration=ConfigurationFactory.get())


dependenciesFactory = DependenciesFactory()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await DependenciesFactory.build()
    yield
    await dependenciesFactory().shutdown()
