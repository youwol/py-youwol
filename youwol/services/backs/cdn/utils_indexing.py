import asyncio
import itertools
import json
import os
from pathlib import Path
from typing import Dict, Union, Any

from fastapi import HTTPException


skipped_dependencies = []
flatten = itertools.chain.from_iterable


def get_dependencies(path: Union[Path, str]):
    path = str(path)
    # this first case is for backward compatibility, we can safely remove it I believe
    if os.path.exists(path+"/description.json"):
        data = json.loads(open(path+"/description.json").read())
        return [d['id']+"#"+d.get('version', 'x') for d in data["dependencies"] if 'id' in d]

    if os.path.exists(path+"/package.json"):
        data = json.loads(open(path+"/package.json").read())
        if "peerDependencies" not in data:
            return[]
        return [did+"#"+v for did, v in data["peerDependencies"].items() if did not in skipped_dependencies]
    return []


def get_files(path: Union[Path, str]):

    path = str(path)
    p = ["", ""]
    minimized = [o for o in os.listdir(path) if o[-6:] == 'min.js']
    if len(minimized) == 1:
        p[0] = minimized[0]
    if len(minimized) > 1:
        raise Exception("multiple min.js found", path)

    normal = [o for o in os.listdir(path) if o[-3:] == '.js' and '.min.js' not in o]
    if len(normal) == 1:
        p[1] = normal[0]
    return p


def get_library_type(package_json: Any):

    allowed_types = ['library', 'flux-pack', 'library-core', 'application']
    name = package_json['name']

    if name in ["rxjs", "lodash", "reflect-metadata", "tslib", "bootstrap"]:
        return "core_library"

    if 'youwol' in package_json \
            and 'type' in package_json['youwol']\
            and package_json['youwol']['type'] in allowed_types:
        return package_json['youwol']['type']

    if 'youwol' in package_json \
            and 'type' in package_json['youwol'] \
            and package_json['youwol']['type'] not in allowed_types:
        raise HTTPException(500, f"package.json->youwol->type must be in {allowed_types}")
    return "library"


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_version_number(version_str: str) -> int:
    delta = 0
    if "-next" in version_str:
        delta = 1
        version_str = version_str.split("-")[0]
    return int(int(version_str.split('.')[0])*1e7 + int(version_str.split('.')[1])*1e4 +
               int(version_str.split('.')[2])*10 + delta)


def get_library_id(name: str, version: str) -> str:
    return name + "#" + version


def format_doc_db_record(package_path: Path, fingerprint: str) -> Dict[str, str]:

    package_json = json.loads(package_path.read_bytes())

    name = package_json.get("name", None)
    version = package_json.get("version", None)
    if not name or not version:
        raise HTTPException(500, f"{name}@{version}: package.json needs a 'name' and 'version' properties")

    main = package_json.get("main", None)

    if not main:
        raise HTTPException(500, f"{name}@{version}: package.json needs a 'main' property pointing to the module " +
                            "entry point.")

    def get_cdn_dependencies() -> Dict[str, str]:
        if 'youwol' in package_json and 'cdnDependencies' in package_json['youwol']:
            return package_json['youwol']['cdnDependencies']
        return {}

    namespace = "" if '@' not in name else name.split("/")[0].split("@")[1]
    path = Path("libraries") / namespace / name.split("/")[-1] / version
    return {
        "library_id": name + '#' + version,
        "library_name": name,
        "namespace": namespace,
        "version": version,
        "description": package_json.get("description", ""),
        "tags": package_json.get("keywords", []),
        "type": get_library_type(package_json),
        "dependencies": [k+"#"+v for k, v in get_cdn_dependencies().items()],
        "bundle_min": "",
        "bundle": str(main),
        "version_number": get_version_number(version),
        "path": str(path),
        "fingerprint": fingerprint
        }


async def post_indexes(doc_db, data, count, headers):

    for chunk in chunks(data, count):
        await asyncio.gather(*[doc_db.create_document(d, owner="/youwol-users", headers=headers) for d in chunk])
