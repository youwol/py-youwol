from pathlib import Path
from typing import Union, List, Callable, Dict, Set, Type

from pydantic import BaseModel

from youwol.configuration.models_base import (
    Install, Build, Action, FileListing, Target,
    Pipeline, resolve_category, StepEnum, Asset, Skeleton,
    )
from youwol_utils import JSON

Package = 'youwol.routers.packages.models.Package'
Context = 'youwol.context.Context'
YouwolConfiguration = 'youwol.configuration.youwol_configuration.YouwolConfiguration'


class InstallPackage(Install):
    isInstalled: Callable[[Package, Context], bool] = None


class BuildPackage(Build):

    checkSum: Union[List[str], FileListing] = None
    dist: str = "dist"
    sourceNodeModules: Union[str, Path] = None
    destinationNodeModules: List[Union[str, Path]] = None
    package_json: Callable[[JSON, Package, Context], JSON] = None


class TestPackage(Action):
    pass


class CDNPackage(BaseModel):

    targets:  Union[List[str], FileListing] = None


class PipelinePackage(Pipeline):
    documentation: Callable[[Package], Union[str, Path]] = None
    install: Union[InstallPackage, None] = None
    build: Union[BuildPackage, None] = None
    test: Union[TestPackage, None] = None
    cdn: Union[CDNPackage, None] = None


class TargetPackage(Target):
    pass


class InfoPackage(BaseModel):
    name: str
    version: str
    main: str = None
    files: List[str] = None
    dependencies: Dict[str, str] = {}
    peerDependencies: Dict[str, str] = {}
    devDependencies: Dict[str, str] = {}
    projectDependencies: Dict[str, str] = {}


class Packages(Asset):

    def steps(self) -> Set[StepEnum]:
        return {StepEnum.INSTALL, StepEnum.BUILD, StepEnum.TEST, StepEnum.CDN}

    def PipelineType(self) -> Type:
        return PipelinePackage

    pipelines: Dict[str, PipelinePackage] = {}
    targets: Dict[str, List[TargetPackage]] = {}

    async def pipeline(self,
                       category: str,
                       target: TargetPackage,
                       info: InfoPackage,
                       context: Context
                       ) -> PipelinePackage:

        return await resolve_category(
            self,
            category=category,
            target=target,
            info=info,
            context=context
            )
