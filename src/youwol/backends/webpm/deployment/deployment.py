# third parties
from fastapi import APIRouter

# Youwol backends
from youwol.backends.common import BackendDeployment


class WebpmDeployment(BackendDeployment):
    def __init__(self, router: APIRouter):
        self.__router = router

    def name(self) -> str:
        return "webpm"

    def router(self) -> APIRouter:
        return self.__router
