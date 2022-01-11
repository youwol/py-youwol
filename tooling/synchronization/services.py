import glob
import itertools
import os
import shutil
from pathlib import Path
from typing import NamedTuple, List


flatten = itertools.chain.from_iterable


class ServiceInjection(NamedTuple):
    src: Path
    dst: Path
    include: List[str] = []


def included_services(platform_path, open_source_path):

    src_backend_services = platform_path / 'services'
    dst_services = open_source_path / 'python' / 'py-youwol' / 'youwol' / 'services'

    return [
        ServiceInjection(
            src=src_backend_services / 'cdn-backend' / 'src' / 'youwol_cdn',
            dst=dst_services / 'backs' / 'cdn',
            include=["/__init__.py", "/models.py", "/resources_initialization.py", "/root_paths.py", "/utils*"]
            ),
        ServiceInjection(
            src=src_backend_services / 'treedb-backend' / 'src' / 'youwol_treedb',
            dst=dst_services / 'backs' / 'treedb',
            include=["/__init__.py", "/models.py", "/root_paths.py", "/utils.py"]
            ),
        ServiceInjection(
            src=src_backend_services / 'assets-backend' / 'src' / 'youwol_assets',
            dst=dst_services / 'backs' / 'assets',
            include=["/__init__.py", "/models.py", "/root_paths.py", "/utils.py"]
            ),
        ServiceInjection(
            src=src_backend_services / 'flux-backend' / 'src' / 'youwol_flux',
            dst=dst_services / 'backs' / 'flux',
            include=["/__init__.py", "/models.py", "/root_paths.py", "/suggestions.py", "/utils.py",
                     "/workflow_new_project.py", "/backward_compatibility.py"]
            ),
        ServiceInjection(
            src=src_backend_services / 'assets-gateway' / 'src' / 'youwol_assets_gateway',
            dst=dst_services / 'backs' / 'assets_gateway',
            include=["/__init__.py", "/models.py", "/root_paths.py", "/package_drive.py", "/utils.py",
                     "/all_icons_emojipedia.py", "/raw_stores/*", "/routers/*"]
            ),
        ServiceInjection(
            src=src_backend_services / 'stories-backend' / 'src' / 'youwol_stories',
            dst=dst_services / 'backs' / 'stories',
            include=["/__init__.py", "/models.py", "/root_paths.py", "/utils.py", "/all_icons_emojipedia.py"]
            ),
        ServiceInjection(
            src=src_backend_services / 'cdn-apps-server' / 'src' / 'youwol_cdn_apps_server',
            dst=dst_services / 'backs' / 'cdn_apps_server',
            include=["/__init__.py", "/root_paths.py"]
            )
        ]


def sync_services(platform_path: Path, open_source_path: Path):

    services = included_services(platform_path, open_source_path)

    for service in services:

        files = flatten([glob.glob(str(platform_path / service.src) + pattern, recursive=True)
                         for pattern in service.include])
        files = list(files)

        for file in files:
            destination = platform_path / service.dst / Path(file).relative_to(platform_path / service.src)
            if Path(file).is_file():
                if not destination.parent.exists():
                    os.makedirs(name=destination.parent)
                shutil.copy(src=file, dst=destination)
            else:
                os.makedirs(destination, exist_ok=True)
