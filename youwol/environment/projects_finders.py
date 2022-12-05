from pathlib import Path
from typing import Union, List

from youwol.environment.paths import PathsBook
from youwol_utils.utils_paths import FileListing, matching_files


def auto_detect_projects(paths_book: PathsBook, root_folder: Union[Path, str], ignore: List[str] = None) -> List[Path]:
    database_ignore = None
    system_ignore = None
    root_folder = Path(root_folder)
    if not root_folder.exists():
        return []

    try:
        database_ignore = paths_book.databases.relative_to(root_folder)
    except ValueError:
        pass
    try:
        system_ignore = paths_book.system.relative_to(root_folder)
    except ValueError:
        pass

    ignore = (ignore or []) + [str(path) for path in [database_ignore, system_ignore] if path]
    file_listing = FileListing(
        include=["**/.yw_pipeline/yw_pipeline.py"],
        ignore=["**/node_modules", "**/.template", "**/.git"] + ignore
    )
    yw_pipelines = matching_files(root_folder, file_listing)
    return [p.parent.parent for p in yw_pipelines]
