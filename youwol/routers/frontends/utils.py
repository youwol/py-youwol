import asyncio
import functools
import itertools
import os
from pathlib import Path
from typing import List

import aiohttp
from aiohttp import ClientConnectorError
from pydantic import BaseModel

from youwol.configuration.models_front import TargetFront, InfoFront, PipelineFront
from youwol.context import Context, ActionStep
from youwol.utils_misc import merge

flatten = itertools.chain.from_iterable


class FrontEnd(BaseModel):
    assetId: str
    pipeline: PipelineFront
    target: TargetFront
    info: InfoFront


async def get_all_fronts(context: Context) -> List[FrontEnd]:

    if 'all_fronts' in context.config.cache:
        return context.config.cache['all_fronts']

    config = context.config
    all_fronts = flatten([[(pipeline, front) for front in fronts]
                          for pipeline, fronts in config.userConfig.frontends.targets.items()])
    all_fronts = list(all_fronts)

    def to_info(t: TargetFront):
        name = Path(t.folder).name
        return InfoFront(name=name, port=t.port or get_port_number(name))

    all_info = [to_info(t) for _, t in all_fronts]

    async def to_front(category: str, target: TargetFront, info: InfoFront):
        return FrontEnd(
            assetId=info.name,
            pipeline=await config.userConfig.frontends.pipeline(category, target, info,
                                                                context.with_target(info.name)),
            target=target,
            info=info
            )

    all_fronts = [await to_front(category, target, info) for (category, target), info in zip(all_fronts, all_info)]
    context.config.cache['all_fronts'] = all_fronts
    return all_fronts


async def ping(url: str):
    try:
        async with aiohttp.ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as _:
                return True
    except ClientConnectorError:
        return False


async def serve(front: FrontEnd, context: Context):

    folder = front.target.folder
    p = await asyncio.create_subprocess_shell(front.pipeline.serve.run,
                                              cwd=str(folder),
                                              stdout=asyncio.subprocess.PIPE,
                                              stderr=asyncio.subprocess.PIPE,
                                              shell=True)

    async for f in merge(p.stdout, p.stderr):
        await context.info(ActionStep.RUNNING, content=f.decode('utf-8'))


async def kill(front: FrontEnd):
    os.system("kill -9 `lsof -t -i:{}`".format(front.target.port))


def get_port_number(name: str):
    port = functools.reduce(lambda acc, e: acc + ord(e), name, 0)
    # need to check if somebody is already listening
    return 3000 + port % 1000
