# standard library
import asyncio

from asyncio.subprocess import Process
from collections.abc import Awaitable, Callable

# third parties
from aiostream import stream

# Youwol utilities
from youwol.utils.context import Context


class CommandException(Exception):
    def __init__(self, command: str, outputs: list[str]):
        self.command = command
        self.outputs = outputs
        super().__init__(f"{self.command} failed")


async def execute_shell_cmd(
    cmd: str,
    context: Context,
    log_outputs=True,
    on_executed: Callable[[Process, Context], Awaitable[None]] | None = None,
) -> tuple[int | None, list[str]]:
    async with context.start(
        action="execute 'shell' command", with_labels=["BASH"]
    ) as ctx:
        await ctx.info(text=cmd)
        p = await asyncio.create_subprocess_shell(
            cmd=cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
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
        return p.returncode, outputs
