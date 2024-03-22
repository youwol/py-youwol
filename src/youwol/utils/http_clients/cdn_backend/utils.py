# standard library
import base64

from collections.abc import Iterable
from pathlib import Path

# typing
from typing import cast

# third parties
import brotli

from semantic_version import NpmSpec, Version

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import (
    WebpmLibraryType,
    default_webpm_lib_type,
)
from youwol.utils.types import JSON
from youwol.utils.utils_paths import write_json


def to_std_npm_spec(input_semver: str) -> str:
    """
    Sanitize the provided semantic versioning query regarding youwol specifics.

    Parameters:
        input_semver: a valid NPM specification that may include 'latest' in place of '*'.

    Return:
        Semantic versioning string matching NPM specification.

    Raise:
        `ValueError` if the argument can not be converted to a valid NPM specification.
    """
    base = input_semver.split("-")[0]
    base = base.replace("latest", "*")

    pre_release = (
        "-".join(input_semver.split("-")[1:])
        if len(input_semver.split("-")) > 1
        else None
    )
    semver = f"{base}-{pre_release}" if pre_release else base
    _ = NpmSpec(semver)

    return semver


def is_fixed_version(semver: str):
    """
    Determines if a given semantic versioning query points to a single version.

    This function considers a version fixed if its base (before the first '-', if any) consists of
    exactly three segments separated by dots (e.g., "1.2.3"), and does not include wildcards ("x" or "*")
    or range (">", "<", "^", "~") indicators .


    Parameters:
       semver: The semantic versioning string (following NPM specification) to be evaluated.

    Returns
        True if the version is considered fixed, otherwise False.

    Examples:

    - `is_fixed_version("1.2.3")` returns `True`
    - `is_fixed_version("1.2.x")` returns `False`
    - `is_fixed_version("1.2.3-rc.1")` returns `True`
    - `is_fixed_version("^1.2.3")` returns `False`
    - `is_fixed_version("x")` returns `False`
    """
    base = semver.split("-")[0]

    if len(base.split(".")) != 3:
        return False

    fixed = not any(c in base for c in [">", "<", "x", "*", "^", "~"])
    return fixed


async def resolve_version(
    name: str, input_semver: str, versions: Iterable[str], context: Context
) -> str | None:
    """
    This function attempts to find the most appropriate version of a library that matches a specified semantic
    versioning range (input_version). It supports both fixed versions and version ranges. For version ranges,
    it uses the NpmSpec class to filter through the available versions (see notes).
    If the exact version is not found but a work-in-progress (wip) version is available,
    it opts for the wip version.

    Parameters:
        name: The name of the library for which the version needs to be resolved.
        input_semver: The semantic versioning range or fixed version number specified for the library.
        versions: A collection of available version strings for the library.
        context: Current context object for logging and tracking the version resolution process.

    Return:
        The most appropriate version string based on the input version range and available versions.
        Returns None if no suitable version is found.

    Notes:
    - The function assumes versions may include "-wip" postfixes to denote work-in-progress versions.
    - The `input_semver` is a slightly extended NPM specification, see [to_std_npm_spec](@yw-nav-func:to_std_npm_spec).
    """

    async with context.start(
        action="resolve_version", with_attributes={"library": name}
    ) as ctx:
        version_spec = to_std_npm_spec(input_semver=input_semver)
        if is_fixed_version(input_semver):
            return input_semver

        selector = NpmSpec(version_spec)
        typed_version = next(
            selector.filter(Version(v.replace("-wip", "")) for v in versions), None
        )
        if not typed_version:
            return None
        if str(typed_version) not in versions and f"{typed_version}-wip" in versions:
            await ctx.info(
                f"{typed_version} not available => using {typed_version}-wip"
            )
            typed_version = Version(f"{typed_version}-wip")

        await ctx.info(
            text=f"Use latest compatible version of {name}#{input_semver} : {typed_version}"
        )
        return str(typed_version)


def create_local_scylla_db_docs_file_if_needed(expected_path: Path):
    if not expected_path.exists():
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(data={"documents": []}, path=expected_path)
    return expected_path


async def encode_extra_index(documents: list[JSON], context: Context):
    async with context.start(action="encode_extra_index") as ctx:

        def flatten_elem(d: JSON) -> str:
            if not isinstance(d, dict):
                raise ValueError("Not a dictionary")
            lib_type = get_library_type(d["type"])
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
                + f"&{lib_type}"
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
    async with context.start(action="decode_extra_index") as ctx:
        b = base64.b64decode(documents)
        extra = brotli.decompress(b)
        src_str = extra.decode("utf-8")

        def unflatten_elem(elem: str):
            props: list[str] = elem.split("&")
            return {
                "library_name": props[0],
                "version": props[1],
                "bundle": props[2],
                "fingerprint": props[3],
                "dependencies": [d for d in props[4][1:-1].split(",") if d != ""],
                "aliases": [d for d in props[5][1:-1].split(",") if d != ""],
                # The next check is to make py-youwol<0.1.8 compatible with the remote cdn backend.
                # Can be removed when py-youwol<0.1.8 are not supported anymore.
                "type": (
                    get_library_type(props[6])
                    if len(props) > 6
                    else default_webpm_lib_type
                ),
            }

        list_documents = [unflatten_elem(d) for d in src_str.split(";")]
        await ctx.info(f"Decoded extra index with {len(list_documents)} elements")
        return list_documents


def get_library_type(lib_type: str) -> WebpmLibraryType:
    # This is for backward compatibility purposes.
    # Can be replaced by `return lib_type` when TG-2081  is closed
    return (
        cast(WebpmLibraryType, lib_type)
        if lib_type in {"js/wasm", "backend", "pyodide"}
        else default_webpm_lib_type
    )
