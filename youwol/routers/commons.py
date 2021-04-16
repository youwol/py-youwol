from typing import List, Dict, Any

from pydantic import BaseModel

from youwol.configuration.models_base import SkeletonParameter, Pipeline
from youwol.configuration.youwol_configuration import YouwolConfigurationFactory, yw_config
from youwol.context import Context

from youwol.routers.environment.router import status as env_status


class SkeletonResponse(BaseModel):
    name: str
    description: str
    parameters: List[SkeletonParameter]


class SkeletonsResponse(BaseModel):
    skeletons: List[SkeletonResponse]


class PostSkeletonBody(BaseModel):
    parameters: Dict[str, Any]


async def list_skeletons(
        pipelines: Dict[str, Pipeline]
        ):
    resp_skeletons = [
        SkeletonResponse(name=name, description=p.skeleton.description, parameters=p.skeleton.parameters)
        for name, p in pipelines.items() if p.skeleton
        ]

    return SkeletonsResponse(skeletons=resp_skeletons)


async def create_skeleton(
        body: PostSkeletonBody,
        pipeline: Pipeline,
        context: Context
        ):

    skeleton = pipeline.skeleton
    await skeleton.generate(pipeline.skeleton.folder, body.parameters, pipeline, context)
    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(context.request, new_conf)
    return {}
