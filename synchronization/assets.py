import base64
import itertools
import json

import shutil
import time
from pathlib import Path
from typing import Any

from synchronization.cdn import included_packages
from youwol.utils_paths import parse_json


def to_id(package_name: str) -> str:
    b = str.encode(package_name)
    return base64.urlsafe_b64encode(b).decode()


flatten = itertools.chain.from_iterable

group_id = "L3lvdXdvbC11c2Vycw=="  # /youwol-users


def packages_children(platform_path: Path):

    def get_kind(package_json):
        if 'youwol' in package_json and 'type' in package_json['youwol']:
            return package_json['youwol']['type']
        return 'library'

    src_databases = platform_path.parent / 'drive-shared' / 'storage' / 'cdn' / 'youwol-users' / 'libraries'
    packages_json = [parse_json(src_databases / path / 'package.json') for path in included_packages]
    names = [p['name'] for p in packages_json]
    kinds = [get_kind(p) for p in packages_json]
    asset_ids = [to_id(to_id(name)) for name in names]
    return {
        "libraries": [{"type": "asset", "id": asset_id, "_name": name}
                      for name, asset_id, kind in zip(names, asset_ids, kinds) if kind == "library"],
        "flux-packs": [{"type": "asset", "id": asset_id, "_name": name}
                       for name, asset_id, kind in zip(names, asset_ids, kinds) if kind == "flux-pack"]
        }


def get_data(platform_path: Path):
    packages = packages_children(platform_path)
    return {
        "type": "drive",
        "id": "py-youwol-drive-youwol-users",
        "name": "assets",
        "children": [
            {
                "type": "folder",
                "id": "py-youwol-folder-packages",
                "name": "packages",
                "children": packages['libraries']
                },
            {
                "type": "folder",
                "id": "py-youwol-folder-modules-box",
                "name": "modules-box",
                "children": packages['flux-packs']
                }
            ]
        }


def flatten_asset(drive, folder: Any = None):
    folder = folder or drive
    direct_assets = [{"assetId": c["id"], "driveId": drive["id"], "folderId": folder["id"], "_name":c['_name']}
                     for c in folder["children"] if c["type"] == "asset"]

    return list(flatten(flatten_asset(drive, f)
                        for f in folder["children"] if f["type"] == "folder")) + direct_assets


def flatten_folders(drive, parent: Any = None, folder: Any = None):

    folder = folder or drive
    parent = parent or drive
    direct_folders = [{"folder_id": c["id"],
                       "name":c["name"],
                       "parent_folder_id": parent["id"],
                       "type":"",
                       "metadata":"",
                       "drive_id": drive["id"],
                       "group_id": group_id,
                       "owner": "/youwol-users",
                       }
                      for c in folder["children"] if c["type"] == "folder"]

    return list(flatten(flatten_folders(drive, folder, f)
                        for f in folder["children"] if f["type"] == "folder")) + direct_folders


def flatten_drives(drive):

    return [{
        "name": drive["name"],
        "drive_id": drive["id"],
        "metadata":"",
        "owner": "/youwol-users",
        "group_id": group_id
        }]


def get_asset(input_asset, src_data):

    asset = next((e for e in src_data['documents'] if e['asset_id'] == input_asset['assetId']), None)
    if not asset:
        print("Can not find asset for", input_asset['_name'])
    return asset


def get_access_policy(assets_data):

    return {
        "asset_id": assets_data["asset_id"],
        "related_id": assets_data["related_id"],
        "consumer_group_id": "*",
        "read": "authorized",
        "share": "authorized",
        "parameters": "{}",
        "timestamp": int(time.time()),
        "owner": "/youwol-users"
        }


def to_treedb_item(asset: Any, drive_id: str, folder_id: str):

    meta = {
        "assetId": asset["asset_id"],
        "relatedId": asset["related_id"],
        "borrowed": True
        }
    return {
            "item_id": asset["asset_id"],
            "folder_id": folder_id,
            "name":  asset["name"],
            "type": "package",
            "metadata": json.dumps(meta),
            "owner": "/youwol-users",
            "drive_id": drive_id,
            "group_id": group_id,
            "related_id": asset["asset_id"]
        }


def copy_assets(platform_path: Path, system_path: Path):

    src_base = platform_path / '..' / 'drive-shared'
    src_docdb = src_base / 'docdb' / 'assets' / 'entities'
    src_storage = src_base / 'storage' / 'assets' / 'youwol-users' / 'package'

    dst_base = system_path / 'databases'
    dst_docdb_access = dst_base/'docdb'/'assets'/ 'access_policy'
    dst_docdb_assets = dst_base / 'docdb' / 'assets' / 'entities'
    dst_storage_assets = dst_base / 'storage' / 'assets' / 'youwol-users' / 'package'

    src_data = parse_json(src_docdb / 'data.json')
    data = get_data(platform_path=platform_path)
    assets_meta = [e for e in flatten_asset(data, data)]
    assets_data = [get_asset(asset, src_data) for asset in assets_meta]

    with open(dst_docdb_assets/'data.json', 'w') as file:
        json.dump({"documents": [asset for asset in assets_data if asset is not None]}, file, indent=4)

    for asset in assets_meta:
        if not (dst_storage_assets / asset['assetId']).exists() and (src_storage / asset['assetId']).exists():
            shutil.copytree(src=src_storage / asset['assetId'], dst=dst_storage_assets / asset['assetId'])

    assets_access = [get_access_policy(asset) for asset in assets_data if asset]
    with open(dst_docdb_access/'data.json', 'w') as file:
        json.dump({"documents": [asset for asset in assets_access if asset is not None]}, file, indent=4)

    treedb_items = [to_treedb_item(asset, asset_meta['driveId'], asset_meta['folderId'])
                    for asset, asset_meta in zip(assets_data, assets_meta) if asset is not None]

    dst_docdb_treedb_items = dst_base/'docdb'/'tree_db'/'items'
    with open(dst_docdb_treedb_items/'data.json', 'w') as file:
        json.dump({"documents": treedb_items}, file, indent=4)

    treedb_folders = flatten_folders(data)
    dst_docdb_treedb_folders = dst_base/'docdb'/'tree_db'/'folders'
    with open(dst_docdb_treedb_folders/'data.json', 'w') as file:
        json.dump({"documents": treedb_folders}, file, indent=4)

    treedb_drives = flatten_drives(data)
    dst_docdb_treedb_drives = dst_base/'docdb'/'tree_db'/'drives'
    with open(dst_docdb_treedb_drives/'data.json', 'w') as file:
        json.dump({"documents": treedb_drives}, file, indent=4)



