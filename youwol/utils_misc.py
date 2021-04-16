import asyncio
import traceback
from pathlib import Path
from typing import Dict, Any, Callable, Union, Awaitable

from youwol.context import Context, ActionStep, UserCodeException
from youwol.routers.packages.models import Package
from youwol.utils_low_level import merge

TKey = Any
TValue = Any
TResult = Any

YouwolConfiguration = 'youwol.dashboard.back.configuration.youwol_configuration.YouwolConfiguration'


def map_values(dic: Dict[TKey, TValue], map_fct: Callable[[TKey], TResult]) -> Dict[TKey, TResult]:
    return {k: map_fct(v) for k, v in dic.items()}


async def run_cmd_async(
        cmd: str,
        folder: Union[Path, str],
        context: Context) -> int:

    p = await asyncio.create_subprocess_shell(
        cmd=f"(cd {str(folder)} && {cmd})",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True)

    async for f in merge(p.stdout, p.stderr):
        await context.info(ActionStep.RUNNING, f.decode('utf-8'))

    await p.communicate()
    return p.returncode


async def execute_cmd_or_block(
        cmd: Union[str, Callable[[Package, Context], Awaitable[int]]],
        asset: Package,
        context: Context):

    if not isinstance(cmd, str):

        try:
            return_code = await cmd(asset, context)
        except Exception as _:
            raise UserCodeException("Exception while running custom block.", traceback.extract_stack())

        if return_code > 0:
            await context.abort(f"Running custom block failed.")

        return return_code

    folder = asset.target.folder

    p = await asyncio.create_subprocess_shell(
        cmd=f"(cd  {str(folder)} && {cmd} )",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True
        )

    async for f in merge(p.stdout, p.stderr):
        await context.info(ActionStep.RUNNING, f.decode('utf-8'))

    await p.communicate()

    if p.returncode > 0:
        await context.abort(f"Running cmd {cmd} failed.")

    return p.returncode
