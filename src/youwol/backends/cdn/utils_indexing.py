# standard library
import asyncio
import itertools
import json
import os

from pathlib import Path

# typing
from typing import Any, Union

# third parties
import semantic_version

from fastapi import HTTPException

# Youwol utilities
from youwol.utils.context import Context

# relative
from .configurations import Constants

flatten = itertools.chain.from_iterable


def get_files(path: Union[Path, str]):
    path = str(path)
    p = ["", ""]
    minimized = [o for o in os.listdir(path) if o.endswith("min.js")]
    if len(minimized) == 1:
        p[0] = minimized[0]
    if len(minimized) > 1:
        raise RuntimeError("multiple min.js found", path)

    normal = [o for o in os.listdir(path) if o.endswith(".js") and ".min.js" not in o]
    if len(normal) == 1:
        p[1] = normal[0]
    return p


def get_library_type(package_json: Any):
    allowed_types = ["library", "flux-pack", "library-core", "application"]
    name = package_json["name"]

    if name in ["rxjs", "lodash", "reflect-metadata", "tslib", "bootstrap"]:
        return "core_library"

    if (
        "youwol" in package_json
        and "type" in package_json["youwol"]
        and package_json["youwol"]["type"] in allowed_types
    ):
        return package_json["youwol"]["type"]

    if (
        "youwol" in package_json
        and "type" in package_json["youwol"]
        and package_json["youwol"]["type"] not in allowed_types
    ):
        raise HTTPException(
            500, f"package.json->youwol->type must be in {allowed_types}"
        )
    return "library"


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def get_version_number(version_str: str) -> int:
    delta = 0
    version = semantic_version.Version(version_str)
    if version.prerelease:
        prerelease = version.prerelease[0]
        # 'next' deprecated: for backward compatibility (10/03/2022)
        delta = (
            1
            if prerelease == "next"
            else -(1 + Constants.allowed_prerelease.index(prerelease))
        )

    return int(version.major * 1e7 + version.minor * 1e4 + version.patch * 10 + delta)


def get_version_number_str(version_str: str) -> str:
    base = str(get_version_number(version_str))
    version = "0" * (10 - len(base)) + base
    return version


def get_library_id(name: str, version: str) -> str:
    return name + "#" + version


async def format_doc_db_record(
    package_path: Path, fingerprint: str, context: Context
) -> dict[str, Union[str, list[str]]]:
    package_json = json.loads(package_path.read_bytes())

    name = package_json.get("name", None)
    version = package_json.get("version", None)
    if not name or not version:
        raise HTTPException(
            500,
            f"{name}@{version}: package.json needs a 'name' and 'version' properties",
        )

    main = package_json.get("main", None)

    if not main:
        raise HTTPException(
            500,
            f"{name}@{version}: package.json needs a 'main' property pointing to the module "
            + "entry point.",
        )

    async def get_webpm_dependencies() -> dict[str, str]:
        if "webpm" in package_json and "dependencies" in package_json["webpm"]:
            return package_json["webpm"]["dependencies"]
        if "youwol" in package_json and "cdnDependencies" in package_json["youwol"]:
            await context.warning(
                text="'youwol' attribute in 'package.json' is deprecated, it should be replaced by 'webpm'"
            )
            return package_json["youwol"]["cdnDependencies"]
        return {}

    def get_webpm_aliases() -> list[str]:
        if "webpm" in package_json and "aliases" in package_json["webpm"]:
            return package_json["webpm"]["aliases"]
        return []

    namespace = "" if "@" not in name else name.split("/")[0].split("@")[1]
    path = Path("libraries") / namespace / name.split("/")[-1] / version
    dependencies = await get_webpm_dependencies()
    return {
        "library_id": name + "#" + version,
        "library_name": name,
        "namespace": namespace,
        "version": version,
        "aliases": get_webpm_aliases(),
        "description": package_json.get("description", ""),
        "tags": package_json.get("keywords", []),
        "type": get_library_type(package_json),
        "dependencies": [k + "#" + v for k, v in dependencies.items()],
        "bundle_min": "",
        "bundle": str(main),
        "version_number": get_version_number_str(version),
        "path": str(path),
        "fingerprint": fingerprint,
    }


async def post_indexes(doc_db, data, count, headers):
    for chunk in chunks(data, count):
        await asyncio.gather(
            *[
                doc_db.create_document(d, owner="/youwol-users", headers=headers)
                for d in chunk
            ]
        )
