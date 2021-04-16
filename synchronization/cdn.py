import json
import os
import shutil
from pathlib import Path

from youwol.utils_paths import parse_json

included_packages = [
    "bootstrap/4.4.1",
    "d3/5.15.0",
    "fontawesome/5.12.1",
    "grapes/0.16.2",
    "jquery/3.2.1",
    "lodash/4.17.15",
    "plotly.js-gl2d-dist-min/1.51.1",
    "popper.js/1.12.9",
    "reflect-metadata/0.1.13",
    "rxjs/6.5.5",
    "three/0.114.0",
    "tslib/1.10.0",
    "three-trackballcontrols/0.0.8",
    "youwol/attribute/0.1.5",
    "youwol/cdn-client/0.0.2",
    "youwol/flux-lib-core/1.7.2",
    "youwol/flux-lib-views/0.7.22",
    "youwol/flux-pack-3d-basics/1.1.7",
    "youwol/flux-pack-dataframe/0.0.8",
    "youwol/flux-pack-flows-std/1.1.2",
    "youwol/flux-pack-io/0.1.4",
    "youwol/flux-pack-kepler/1.3.8",
    "youwol/flux-pack-plotly/1.0.9",
    "youwol/flux-pack-pmp/0.3.5",
    "youwol/flux-pack-shared-interfaces/0.0.9",
    "youwol/flux-pack-utility-std/1.2.2",
    "youwol/flux-pack-widgets-std/1.3.7",
    "youwol/flux-pack-youwol/0.0.10",
    "youwol/flux-view/0.0.5",
    "youwol/fv-button/0.0.3",
    "youwol/fv-context-menu/0.0.0",
    "youwol/fv-group/0.0.3",
    "youwol/fv-input/0.0.2",
    "youwol/fv-tabs/0.0.2",
    "youwol/fv-tree/0.0.3",
    "youwol/fv-widgets/0.0.3",
    "youwol/geometry/0.1.5",
    "youwol/io/0.1.5",
    "youwol/kepler/1.1.8",
    "youwol/math/0.1.6",
    "youwol/utils/0.1.4",
    "codemirror/5.52.0",
    ]

included_assets = [
    "logo_YouWol_Platform_white.png"
    ]


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

