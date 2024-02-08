# standard library
from contextlib import asynccontextmanager

# third parties
import aiohttp

from fastapi import FastAPI

# Youwol utilities
from youwol.utils import CleanerThread, OidcConfig, PrivateClient, factory_local_cache
from youwol.utils.clients.oidc.tokens_manager import SessionLessTokenManager

# relative
from ..deployment import Configuration, ConfigurationFactory


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


class DependenciesFactory:
    __dependencies: Dependencies | None = None

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
