from pathlib import Path

from tooling.synchronization.services import sync_services

platform_path = Path("/home/greinisch/Projects/platform/")
open_source_path = Path("/home/greinisch/Projects/youwol-open-source/")

sync_services(platform_path, open_source_path)
