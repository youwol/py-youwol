import itertools
from pathlib import Path
from typing import Union, List

from youwol.configuration.defaults import default_path_projects_dir
from youwol.environment.paths import PathsBook
from youwol_utils.utils_paths import FileListing, matching_files


def default_projects_finder(paths_book: PathsBook, root_folders: Union[None, str, Path, List[str], List[Path]] = None):
    if not root_folders:
        (Path.home() / default_path_projects_dir).mkdir(exist_ok=True)

    root_folders = [Path.home() / default_path_projects_dir] if not root_folders else root_folders
    root_folders = root_folders if isinstance(root_folders, List) else [root_folders]
    results = [auto_detect_projects(paths_book=paths_book, root_folder=root_folder, ignore=["**/dist", '**/py-youwol'])
               for root_folder in root_folders]

    return itertools.chain.from_iterable(results)


def auto_detect_projects(paths_book: PathsBook, root_folder: Union[Path, str], ignore: List[str] = None):
    database_ignore = None
    system_ignore = None
    root_folder = Path(root_folder)
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
