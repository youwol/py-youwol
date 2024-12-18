# standard library
import asyncio
import os

from asyncio.subprocess import Process
from collections.abc import Awaitable, Callable

# typing
from typing import cast

# third parties
from aiostream import stream

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.context.models import Label


class CommandException(Exception):
    def __init__(self, command: str, outputs: list[str]):
        self.command = command
        self.outputs = outputs
        super().__init__(f"{self.command} failed.\n\nOutputs:{''.join(outputs)}")


def clone_environ(env_variables: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    return {**env, **env_variables}


async def execute_shell_cmd(
    cmd: str,
    context: Context,
    log_outputs=True,
    on_executed: Callable[[Process, Context], Awaitable[None]] | None = None,
    **kwargs,
) -> tuple[int, list[str]]:

    async with context.start(
        action="execute 'shell' command",
        # BASH is deprecated
        with_labels=["BASH", Label.STD_OUTPUT],
        with_attributes={"cwd": str(kwargs.get("cwd", "None"))},
    ) as ctx:
        await ctx.info(text=cmd)
        p = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
            **kwargs,
        )
        if on_executed:
            await on_executed(p, ctx)
        outputs = []
        async with stream.merge(p.stdout, p.stderr).stream() as messages_stream:
            async for message in messages_stream:
                outputs.append(message.decode("utf-8"))
                if log_outputs:
                    await ctx.info(text=outputs[-1])
        await p.communicate()
        # p.returncode can not be 'None' as the process has terminated
        return_code = cast(int, p.returncode)
        return return_code, outputs
