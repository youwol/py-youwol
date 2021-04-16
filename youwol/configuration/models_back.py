from typing import List, Callable, Dict, Set, Type

from pydantic import BaseModel

from youwol.configuration.models_base import (
    Install, Build, Action,
    Pipeline, resolve_category, Asset, StepEnum,
    )
from youwol.configuration.models_service import TargetService, Serve


BackEnd = 'youwol.routers.backends.utils.BackEnd'
Context = 'youwol.dashboard.back.context.Context'


class InstallBack(Install):
    pass


class BuildBack(Build):
    pass


class TestBack(Action):
    pass


class ServeBack(Serve):
    pass


class PipelineBack(Pipeline):
    install: InstallBack = None
    build: BuildBack = None
    test: TestBack = None
    serve: ServeBack = None


class TargetBack(TargetService):
    pass


class InfoBack(BaseModel):
    name: str
    port: int


YouwolConfiguration = 'YouwolConfiguration'


class HeadersBackend(BaseModel):
    values: Callable[[Context], Dict[str, str]]
    enableCaching: bool = True


class BackEnds(Asset):

    def steps(self) -> Set[StepEnum]:
        return {StepEnum.INSTALL, StepEnum.BUILD, StepEnum.TEST, StepEnum.SERVE}

    def PipelineType(self) -> Type:
        return PipelineBack

    headers: HeadersBackend = None
    pipelines: Dict[str, PipelineBack] = {}
    targets: Dict[str, List[TargetBack]] = {}

    async def pipeline(self,
                       category: str,
                       target: TargetBack,
                       info: InfoBack,
                       context: Context
                       ) -> PipelineBack:

        return await resolve_category(
            self,
            category=category,
            target=target,
            info=info,
            context=context
            )
