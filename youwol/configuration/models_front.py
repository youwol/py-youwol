from typing import List, Dict, Set, Type, Callable

from pydantic import BaseModel

from youwol.configuration.models_base import (
    Install, Build, Action,
    Pipeline, resolve_category, StepEnum, Asset,
    )
from youwol.configuration.models_service import TargetService


FrontEnd = 'youwol.routers.frontends.utils.FrontEnd'
Context = 'youwol.dashboard.back.context.Context'
YouwolConfiguration = 'youwol.dashboard.back.configuration.youwol_configuration.YouwolConfiguration'


class InstallFront(Install):
    isInstalled: Callable[[FrontEnd, Context], bool] = lambda _resource, _ctx: True


class BuildFront(Build):
    dist: str = None


class TestFront(Action):
    pass


class ServeFront(Action):
    pass


class PipelineFront(Pipeline):
    install: InstallFront = None
    build: BuildFront = None
    test: TestFront = None
    serve: ServeFront = None


class TargetFront(TargetService):
    pass


class InfoFront(BaseModel):
    name: str
    port: int


class FrontEnds(Asset):

    def steps(self) -> Set[StepEnum]:
        return {StepEnum.INSTALL, StepEnum.BUILD, StepEnum.TEST, StepEnum.SERVE}

    def PipelineType(self) -> Type:
        return PipelineFront

    pipelines: Dict[str, PipelineFront] = {}
    targets: Dict[str, List[TargetFront]] = {}

    async def pipeline(self,
                       category: str,
                       target: TargetFront,
                       info: InfoFront,
                       context: Context
                       ) -> PipelineFront:

        return await resolve_category(
            self,
            category=category,
            target=target,
            info=info,
            context=context
            )
