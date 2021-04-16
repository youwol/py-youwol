import functools
import itertools
import os
from pathlib import Path
from typing import List

import aiohttp
from aiohttp import ClientConnectorError
from pydantic import BaseModel

from youwol.configuration.models_back import PipelineBack, InfoBack, TargetBack
from youwol.context import Context
from youwol.routers.backends.models import TargetStatus, InstallStatus

flatten = itertools.chain.from_iterable


class BackEnd(BaseModel):
    assetId: str
    pipeline: PipelineBack
    target: TargetBack
    info: InfoBack


async def get_all_backends(context: Context) -> List[BackEnd]:

    if 'all_backs' in context.config.cache:
        return context.config.cache['all_backs']

    config = context.config
    all_backs = flatten([[(pipeline, front) for front in fronts]
                         for pipeline, fronts in config.userConfig.backends.targets.items()])
    all_backs = list(all_backs)

    def to_info(t: TargetBack):
        return InfoBack(name=Path(t.folder).name, port=get_port_number(t))

    all_info = [to_info(t) for _, t in all_backs]

    async def to_backend(category: str, target: TargetBack, info: InfoBack):
        return BackEnd(
            assetId=info.name,
            pipeline=await config.userConfig.backends.pipeline(category, target, info,
                                                               context.with_target(info.name)),
            target=target,
            info=info
            )

    all_backs = [await to_backend(category, target, info) for (category, target), info in zip(all_backs, all_info)]

    context.config.cache['all_backs'] = all_backs
    return all_backs


async def ping(url: str):
    try:
        async with aiohttp.ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                return resp.status == 200
    except ClientConnectorError:
        return False


def get_port_number(target: TargetBack):
    name = Path(target.folder).name
    port = functools.reduce(lambda acc, e: acc + ord(e), name, 0)
    # need to check if somebody is already listening
    return 2000 + port % 1000


async def serve(back: BackEnd, context: Context):

    await back.pipeline.serve.exe(resource=back, context=context)


async def kill(back: BackEnd):
    os.system("kill -9 `lsof -t -i:{}`".format(back.target.port))


async def get_status(backend: BackEnd, context: Context) -> TargetStatus:

    installed = await install_status(backend, context)
    return TargetStatus(install_status=installed)


async def install_status(backend: BackEnd, context: Context) -> InstallStatus:

    installed = backend.pipeline.install.is_installed(backend, context)
    return InstallStatus.INSTALLED if installed else InstallStatus.NOT_INSTALLED

