# standard library
from pathlib import Path

# typing
from typing import Iterable, Optional

# third parties
from semantic_version import NpmSpec, Version

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.utils_paths import write_json


def is_fixed_version(version: str):
    base = version.split("-")[0].replace("x", "*").replace("latest", "*")
    fixed = not any(c in base for c in [">", "<", "*", "^", "~"])
    return fixed


async def resolve_version(
    name: str, version: str, versions: Iterable[str], context: Context
) -> Optional[str]:
    async with context.start(
        action="resolve_version", with_attributes={"library": name}
    ) as ctx:  # type: Context
        base = version.split("-")[0].replace("x", "*").replace("latest", "*")
        if is_fixed_version(version):
            return version

        pre_release = "-".join(version.split("-")[1:])
        version_spec = base if len(version.split("-")) == 1 else f"{base}-{pre_release}"
        selector = NpmSpec(version_spec)
        version = next(
            selector.filter(Version(v.replace("-wip", "")) for v in versions), None
        )
        if not version:
            return None
        if str(version) not in versions and f"{version}-wip" in versions:
            await ctx.info(f"{version} not available => use {version}-wip")
            version = Version(f"{version}-wip")

        await ctx.info(
            text=f"Use latest compatible version of {name}#{version} : {version}"
        )
        return str(version)


def create_local_scylla_db_docs_file_if_needed(expected_path: Path):
    if not expected_path.exists():
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(data={"documents": []}, path=expected_path)
    return expected_path
