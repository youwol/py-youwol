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


dst_services = Path(__file__).parent / '..' / '..' / 'youwol' / 'backends'


def included_services(src_backend_services: Path):
    files_base = ["/__init__.py", "/models.py", "/root_paths.py", "/utils.py"]
    return [
        ServiceInjection(
            src=src_backend_services / 'cdn-backend' / 'src' / 'youwol_cdn',
            dst=dst_services / 'cdn',
            include=files_base + ["/resources_initialization.py", "/utils*"]
        ),
        ServiceInjection(
            src=src_backend_services / 'treedb-backend' / 'src' / 'youwol_treedb',
            dst=dst_services / 'treedb',
            include=files_base
        ),
        ServiceInjection(
            src=src_backend_services / 'assets-backend' / 'src' / 'youwol_assets',
            dst=dst_services / 'assets',
            include=files_base
        ),
        ServiceInjection(
            src=src_backend_services / 'flux-backend' / 'src' / 'youwol_flux',
            dst=dst_services / 'flux',
            include=files_base + ["/suggestions.py", "/workflow_new_project.py", "/backward_compatibility.py"]
        ),
        ServiceInjection(
            src=src_backend_services / 'assets-gateway' / 'src' / 'youwol_assets_gateway',
            dst=dst_services / 'assets_gateway',
            include=files_base + ["/package_drive.py", "/all_icons_emojipedia.py", "/raw_stores/*", "/routers/*"]
        ),
        ServiceInjection(
            src=src_backend_services / 'stories-backend' / 'src' / 'youwol_stories',
            dst=dst_services / 'stories',
            include=files_base + ["/all_icons_emojipedia.py"]
        ),
        ServiceInjection(
            src=src_backend_services / 'cdn-apps-server' / 'src' / 'youwol_cdn_apps_server',
            dst=dst_services / 'cdn_apps_server',
            include=files_base
        ),
        ServiceInjection(
            src=src_backend_services / 'cdn-sessions-storage' / 'src' / 'cdn_sessions_storage',
            dst=dst_services / 'cdn_sessions_storage',
            include=files_base
        )
    ]


def sync_services(src_backend_services: Path):
    services = included_services(src_backend_services)

    for service in services[0:1]:

        files = flatten([glob.glob(str(service.src) + pattern, recursive=True)
                         for pattern in service.include])
        files = list(files)

        for file in files:
            destination = service.dst / Path(file).relative_to(src_backend_services / service.src)
            if Path(file).is_file():
                if not destination.parent.exists():
                    os.makedirs(name=destination.parent)
                shutil.copy(src=file, dst=destination.parent)
            else:
                os.makedirs(destination, exist_ok=True)
