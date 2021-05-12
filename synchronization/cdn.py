import json
import os
import shutil
from pathlib import Path

from youwol.utils_paths import parse_json

"""
"three/0.114.0",
"plotly.js-gl2d-dist-min/1.51.1",
"three-trackballcontrols/0.0.8",
"youwol/attribute/0.1.5",
"""

included_packages = [
    "bootstrap/4.4.1",
    "d3/5.15.0",
    "fontawesome/5.12.1",
    "grapes/0.16.2",
    "jquery/3.2.1",
    "lodash/4.17.15",
    "popper.js/1.12.9",
    "reflect-metadata/0.1.13",
    "rxjs/6.5.5",
    "tslib/1.10.0",
    "codemirror/5.52.0",
    "youwol/cdn-client/0.0.4",
    "youwol/flux-svg-plots/0.0.0",
    "youwol/flux-core/0.0.10",
    "youwol/flux-view/0.0.8",
    "youwol/fv-button/0.0.3",
    "youwol/fv-context-menu/0.0.0",
    "youwol/fv-group/0.0.3",
    "youwol/fv-input/0.0.4",
    "youwol/fv-tabs/0.0.2",
    "youwol/fv-tree/0.0.3",
    "youwol/fv-widgets/0.0.3",
    "youwol/flux-files/0.0.4",
    "youwol/flux-code-mirror/0.0.4",
    "youwol/flux-youwol-essentials/0.0.3",
    ]

included_assets = []


def sync_cdn(platform_path: Path, system_path: Path):

    src_databases = platform_path / '..' / 'drive-shared'
    dst_databases = system_path / 'databases'

    os.makedirs(dst_databases / 'docdb' / 'cdn' / 'libraries', exist_ok=True)
    os.makedirs(dst_databases / 'storage' / 'cdn' / 'youwol-users' / 'libraries', exist_ok=True)

    cdn_data = parse_json(src_databases / "docdb" / "cdn" / "libraries" / "data.json")
    cdn_data = [p for p in cdn_data["documents"] if any([path in p['path'] for path in included_packages])]

    with open(dst_databases / 'docdb' / 'cdn' / 'libraries' / 'data.json', 'w') as file:
        json.dump({"documents": cdn_data}, file, indent=4)

    for path in included_packages:
        src = src_databases / 'storage' / 'cdn' / 'youwol-users' / 'libraries' / path
        dst = dst_databases / 'storage' / 'cdn' / 'youwol-users' / 'libraries' / path
        shutil.copytree(src=src, dst=dst)

    os.makedirs(dst_databases / 'storage' / 'cdn' / 'youwol-users' / 'assets')
    for path in included_assets:
        src = src_databases / 'storage' / 'cdn' / 'youwol-users' / 'assets' / path
        dst = dst_databases / 'storage' / 'cdn' / 'youwol-users' / 'assets' / path
        shutil.copy(src=src, dst=dst)

