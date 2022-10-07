from typing import Iterable

from semantic_version import NpmSpec, Version

from youwol_utils import Context


async def resolve_version(
        name: str,
        version: str,
        versions: Iterable[str],
        context: Context
) -> str:

    async with context.start(action="resolve_version",
                             with_attributes={'library': name}) as ctx:  # type: Context

        base = version.split('-')[0].replace('x', '*').replace('latest', '*')
        pre_release = '-'.join(version.split('-')[1:])
        version_spec = base if len(version.split('-')) == 1 else f"{base}-{pre_release}"
        selector = NpmSpec(version_spec)
        version = next(selector.filter(Version(v.replace('-wip', '')) for v in versions), None)
        if str(version) not in versions and f"{version}-wip" in versions:
            await ctx.info(f"{version} not available => use {version}-wip")
            version = Version(f"{version}-wip")

        await ctx.info(text=f"Use latest compatible version of {name}#{version} : {version}")
        return str(version)
