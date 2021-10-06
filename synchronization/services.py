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
    is_front: bool = False


def included_services(platform_path, open_source_path):

    src_backend_services = platform_path / 'services'
    dst_services = open_source_path / 'python' / 'py-youwol' / 'youwol' / 'services'

    return [
        ServiceInjection(
            src=src_backend_services / 'cdn-backend' / 'src' / 'youwol_cdn',
            dst=dst_services / 'backs' / 'cdn',
            include=["/__init__.py", "/models.py", "/resources_initialization.py", "/root_paths.py", "/utils*",
                     "/initial_resources/**/*"]
            ),
        ServiceInjection(
            src=src_backend_services / 'treedb-backend' / 'src'/ 'youwol_treedb',
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
                     "/raw_stores/*", "/routers/*"]
            ),
        ServiceInjection(
            src=Path('..') / 'youwol-open-source' / 'npm' / '@youwol' / 'flux' / 'flux-builder' / 'dist',
            dst=dst_services / 'fronts' / 'flux_builder',
            include=["/*.html", "/*.js", "/*.css", "/*.map"],
            is_front=True
            ),
        ServiceInjection(
            src=Path('..') / 'youwol-open-source' / 'npm' / '@youwol' / 'flux' / 'flux-runner' / 'dist',
            dst=dst_services / 'fronts' / 'flux_runner',
            include=["/*"],
            is_front=True
            ),
        ServiceInjection(
            src=Path('..') / 'youwol-open-source' / 'npm' / '@youwol' / 'workspace-explorer' / 'dist',
            dst=dst_services / 'fronts' / 'workspace_explorer',
            include=["/*"],
            is_front=True
            ),
        ServiceInjection(
            src=open_source_path / 'npm' / '@youwol' / 'dashboard-developer' / 'dist',
            dst=dst_services / 'fronts' / 'dashboard_developer',
            include=["/*"],
            is_front=True
            )
        ]


def sync_services(platform_path: Path, open_source_path: Path):

    services = included_services(platform_path, open_source_path)

    fronts = [s for s in services if s.is_front]

    for front in fronts:
        files = [f for f in os.listdir(platform_path / front.dst)
                 if f != '__init__.py' and not (platform_path / front.dst / f).is_dir()]
        for f in files:
            os.remove(platform_path / front.dst / f)

    for service in services:

        files = flatten([glob.glob(str(platform_path / service.src) + pattern, recursive=True)
                         for pattern in service.include])
        files = list(files)
        if service.is_front:
            shutil.copy(src=platform_path / service.src / '..' / 'package.json',
                        dst=service.dst
                        )

        for file in files:
            destination = platform_path / service.dst / Path(file).relative_to(platform_path / service.src)
            if Path(file).is_file():
                if not destination.parent.exists():
                    os.makedirs(name=destination.parent)
                shutil.copy(src=file, dst=destination)
            else:
                os.makedirs(destination, exist_ok=True)
