# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment

# relative
from .configuration import ConfigurationFactory


class WebpmDeployment(BackendDeployment):
    def __init__(self, router: APIRouter):
        self.__router = router

    def name(self) -> str:
        return "webpm"

    def version(self) -> str:
        return ConfigurationFactory.get().version

    def router(self) -> APIRouter:
        return self.__router
