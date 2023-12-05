# standard library
import base64

from pathlib import Path

# typing
from typing import Iterable, List, Optional

# third parties
import brotli

from semantic_version import NpmSpec, Version

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.types import JSON
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


async def encode_extra_index(documents: List[JSON], context: Context):
    async with context.start(action="encode_extra_index") as ctx:  # type: Context

        def flatten_elem(d: JSON) -> str:
            return (
                "&".join(
                    [d["library_name"], d["version"], d["bundle"], d["fingerprint"]]
                )
                + "&["
                + ",".join(dep for dep in d.get("dependencies", []))
                + "]"
                + "&["
                + ",".join(alias for alias in d.get("aliases", []))
                + "]"
            )

        converted = ";".join([flatten_elem(d) for d in documents])
        src_bytes = converted.encode("utf-8")
        compressed = brotli.compress(src_bytes)
        await ctx.info(
            text="Extra index encoded",
            data={
                "docsCount": len(documents),
                "originalSize": len(src_bytes),
                "compressedSize": len(compressed),
            },
        )
        return base64.b64encode(compressed).decode("utf-8")


async def decode_extra_index(documents: str, context: Context):
    async with context.start(action="decode_extra_index") as ctx:  # type: Context
        b = base64.b64decode(documents)
        extra = brotli.decompress(b)
        src_str = extra.decode("utf-8")

        def unflatten_elem(elem: str):
            props: List[str] = elem.split("&")
            return {
                "library_name": props[0],
                "version": props[1],
                "bundle": props[2],
                "fingerprint": props[3],
                "dependencies": [d for d in props[4][1:-1].split(",") if d != ""],
                "aliases": [d for d in props[5][1:-1].split(",") if d != ""],
            }

        documents = [unflatten_elem(d) for d in src_str.split(";")]
        await ctx.info(f"Decoded extra index with {len(documents)} elements")
        return documents
