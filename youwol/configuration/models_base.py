import asyncio
import collections
import sys
import traceback
from enum import Enum
from functools import reduce
from pathlib import Path
from typing import List, Union, Type, Set, Dict, Any, Callable, Awaitable

from pydantic import BaseModel, Json

from youwol.models import ActionStep
from youwol.utils_low_level import merge

Context = 'youwol.dashboard.back.context.Context'
YouwolConfiguration = 'youwol.dashboard.back.configuration.youwol_configuration.YouwolConfiguration'


class ErrorResponse(BaseModel):

    reason: str
    hints: List[str] = []


def format_unknown_error(reason: str, error: Exception):
    detail = error.args[0]
    error_class = error.__class__.__name__
    cl, exc, tb = sys.exc_info()
    line_number = traceback.extract_tb(tb)[-1][1]
    return ErrorResponse(
        reason=reason,
        hints=[f"{error_class} at line {line_number}: {detail}"]
        )


class Check(BaseModel):
    name: str
    status: Union[bool, ErrorResponse, None] = None


class FormalParameterEnum(Enum):
    STRING = 'STRING'
    ENUM = 'ENUM'


class FormalParameter(BaseModel):
    name: str
    value: Any
    description: str = ""
    meta: Dict[str, Any]


def parameter_enum(name: str, value: str, description: str, values: List[str]):
    return FormalParameter(
        name=name,
        value=value,
        description=description,
        meta={"type": 'ENUM', 'values': values}
        )


class ConfigParameters(BaseModel):
    parameters: Dict[str, FormalParameter]

    def get_values(self) -> Dict[str, Any]:
        return {pid: p.value for pid, p in self.parameters.items()}

    def with_updates(self, new_values: Dict[str, Any]) -> 'ConfigParameters':
        def new_param(pid: str, p: FormalParameter):
            return FormalParameter(name=p.name, description=p.description, meta=p.meta,
                                   value=new_values[pid] if pid in new_values else p.value)
        new_params = {pid: new_param(pid, p) for pid, p in self.parameters.items()}
        return ConfigParameters(parameters=new_params)


class FileListing(BaseModel):
    include: List[str]
    ignore: List[str] = []


class Target(BaseModel):
    folder: Union[Path, str]


class Action(BaseModel):

    run: Union[str, Callable[[Any, Context], str], Callable[[Any, Context], Awaitable]]

    async def exe(self, resource: Any, context: Context):

        if isinstance(self.run, str):
            return await Action.exe_cmd(cmd=self.run, resource=resource, context=context)

        if isinstance(self.run, collections.Callable):
            cmd = self.run(resource, context)
            if isinstance(cmd, str):
                return await Action.exe_cmd(cmd=cmd, resource=resource, context=context)

            return await cmd

    @staticmethod
    async def exe_cmd(cmd: str, resource: Any, context: Context):

        p = await asyncio.create_subprocess_shell(
            cmd=cmd,
            cwd=str(resource.target.folder),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True)

        async for f in merge(p.stdout, p.stderr):
            await context.info(ActionStep.RUNNING, f.decode('utf-8'))

        return await p.communicate()


class Install(Action):
    isInstalled: Callable[[Any, Context], bool] = None

    def is_installed(self, resource, context: Context):
        if self.isInstalled is None:
            return True
        return self.isInstalled(resource, context)


class Build(Action):
    pass


class Test(Action):
    pass


class SkeletonParameter(BaseModel):
    displayName: str
    id: str
    type: str
    required: bool
    description: str
    defaultValue: Any
    placeholder: str


class Skeleton(BaseModel):
    folder: Union[Path, str]
    description: str
    parameters: List[SkeletonParameter]
    generate: Callable[[Path, Dict[str, any], 'Pipeline', Context], Awaitable] = None


class StepEnum(Enum):
    INSTALL = 'install'
    BUILD = 'build'
    TEST = 'test'
    CDN = 'cdn'
    SERVE = 'serve'


class Pipeline(BaseModel):

    skeleton: Union[Skeleton, Callable[[YouwolConfiguration], Skeleton]] = None
    extends: str = None


class Asset(BaseModel):

    def steps(self) -> Set[StepEnum]:
        raise NotImplemented()

    def PipelineType(self) -> Type:
        raise NotImplemented()

    pipelines: Dict[str, Any]


async def resolve_category(
        asset_type: Asset,
        category: str,
        target: Target,
        info: BaseModel,
        context: Context):

    pipeline = asset_type.pipelines[category]
    if not isinstance(pipeline, asset_type.PipelineType()):
        pipeline = asset_type.PipelineType()(** await pipeline(target, info, context))

    if not pipeline.extends:
        return pipeline

    def to_dict(t: Dict[str, Json]):
        r = t or {}
        return {k: v for k, v in r.items() if v}

    extend = await resolve_category(asset_type, pipeline.extends, target, info, context)

    def reduce_fct(acc_merged: Dict[str, Json], step: StepEnum):
        step_name = step.name.lower()
        step_ = {**to_dict(extend.dict()[step.name.lower()]),
                 **to_dict(pipeline.dict()[step.name.lower()])}
        return {**acc_merged, **{step_name: step_}}

    merged = reduce(reduce_fct, asset_type.steps(), {})

    return asset_type.PipelineType()(**merged)
