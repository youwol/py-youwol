import itertools
import json
import os
import shutil
import zipfile
from fnmatch import fnmatch
from json import JSONDecodeError
from os import PathLike
from pathlib import Path
from typing import cast, Union, List, Set, Tuple, Optional, Callable

from appdirs import AppDirs

from youwol_utils.utils_paths import FileListing

flatten = itertools.chain.from_iterable


def copy_tree(source: Path, destination: Path, replace: bool = False):
    # A helper to not having to cast stuffs all the time. See https://youtrack.jetbrains.com/issue/PY-30747
    if replace and os.path.exists(destination):
        shutil.rmtree(destination)
    shutil.copytree(cast(PathLike, source), cast(PathLike, destination))


def copy_file(source: Path, destination: Path, create_folders: bool = False):

    if create_folders and not destination.parent.exists():
        os.makedirs(destination.parent)
    # A helper to not having to cast stuffs all the time. See https://youtrack.jetbrains.com/issue/PY-30747
    shutil.copyfile(cast(PathLike, source), cast(PathLike, destination))


def parse_json(path: Union[str, Path]):
    return json.loads(open(str(path)).read())


def write_json(data: json, path: Path):
    open(str(path), 'w').write(json.dumps(data, indent=4))


def matching_files(
        folder: Union[Path, str],
        patterns: Union[List[str], FileListing]) -> Set[Path]:

    folder = Path(folder)

    def fix_pattern(pattern):
        if (folder / pattern).is_dir():
            return [pattern + "/**/*", pattern + "/*"]
        return [pattern]

    patterns = FileListing(include=[p for p in patterns], ignore=[]) if isinstance(patterns, list) else patterns
    patterns = FileListing(
        include=list(flatten([fix_pattern(p) for p in patterns.include])),
        ignore=list(flatten([fix_pattern(p) for p in patterns.ignore]))
        )
    patterns_folder_include = [p for p in patterns.include if '*' in p]
    patterns_folder_ignore = [p for p in patterns.ignore if '*' in p]

    def is_selected(filepath: Path):
        if any(fnmatch(str(filepath), pattern) for pattern in patterns.ignore):
            return False
        return any(fnmatch(str(filepath), pattern) for pattern in patterns.include)

    def to_skip_branch(path: Path):
        if str(path) == ".":
            return False
        if any(fnmatch(str(path), pattern) for pattern in patterns_folder_ignore):
            return True
        if any(fnmatch(str(path), pattern)for pattern in patterns_folder_include):
            return False
        if any(pattern.startswith(str(path)) for pattern in patterns_folder_include):
            return False
        return True

    selected = []
    patterns_folder_ignore = [p for p in patterns.ignore if '*' in p]
    for root, dirs, files in os.walk(folder):
        root = Path(root).relative_to(folder)
        if to_skip_branch(root):
            dirs[:] = []
            continue
        selected = selected + [folder / root / f for f in files if is_selected(root / f)]

    return selected


def ensure_folders(*paths: Union[str, Path]):
    r = []
    for path in paths:
        p = Path(path)
        os.makedirs(p, exist_ok=True)
        r.append(p)
    return r


def create_zip_file(path: Path, files_to_zip: List[Tuple[Path, str]]):
    zipper = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    for path, name in files_to_zip:
        zipper.write(filename=path, arcname=name)
    zipper.close()


def get_targets(folders: List[Union[str, Path]], pipeline_name: str, target_type: type):

    targets = list(flatten(get_targets_generic(folder, pipeline_name, target_type) for folder in folders))
    return targets


def get_targets_generic(folder: Union[str, Path], pipeline_name: str, target_type: type):

    targets = []
    folder = Path(folder)

    for f in os.listdir(folder):
        if not (folder/f/'package.json').exists():
            continue
        try:
            package_json = parse_json(folder/f/'package.json')
        except JSONDecodeError:
            print(f"Failed to decode package.json: ${folder/f/'package.json'}")
            continue

        if 'youwol' in package_json and \
                "pipeline" in package_json['youwol'] and \
                package_json['youwol']["pipeline"]["name"] == pipeline_name:
            targets.append(target_type(folder=folder/f))

    return targets


app_dirs = AppDirs(appname="py-youwol", appauthor="Youwol")


class PathException(RuntimeError):
    path: str


def default_create_dir(final_path: Path):
    try:
        final_path.mkdir(parents=True)
    except Exception as e:
        raise PathException(f"Error while creating '{str(final_path)}' : {e}")


def fail_on_missing_dir(path: Path):
    raise PathException(f"Not creating missing dir '{str(path)}'")


def ensure_dir_exists(path: Optional[Union[str, Path]],
                      root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                      default_root: Optional[Union[str, Path]] = None,
                      create: Optional[Callable[[Path], None]] = default_create_dir) -> Path:
    path = path if path else "."
    (final_path, exists) = existing_path_or_default(path, root_candidates=root_candidates, default_root=default_root)

    if exists:
        if not final_path.is_dir():
            raise PathException(f"'{str(final_path)}' is not a directory")
    else:
        create(final_path)

    return final_path


def ensure_file_exists(path: Union[str, Path],
                       root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                       default_root: Optional[Union[str, Path]] = None,
                       default_content: Optional[str] = None) -> Path:
    (final_path, exists) = existing_path_or_default(path, root_candidates=root_candidates, default_root=default_root)

    if exists:
        if not final_path.is_file():
            raise PathException(f"'{str(final_path)}' is not a file")
    else:
        if default_content:
            try:
                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_text(default_content)
            except Exception as e:
                raise PathException(f"Error while creating '{str(final_path)}' : {e}")
        else:
            raise PathException(f"'{str(final_path)}' does not exist")

    return final_path


def existing_path_or_default(path: Union[str, Path],
                             root_candidates: Union[Union[str, Path], List[Union[str, Path]]],
                             default_root: Optional[Union[str, Path]] = None) -> (Path, bool):
    typed_path = Path(path)

    if typed_path.is_absolute():
        return typed_path, typed_path.exists()

    if not isinstance(root_candidates, List):
        root_candidates = [root_candidates]

    root_candidates_idx = 0
    while root_candidates_idx < len(root_candidates):
        absolute_path = Path(root_candidates[root_candidates_idx]) / typed_path
        if absolute_path.exists():
            return absolute_path, True
        root_candidates_idx = root_candidates_idx + 1

    final_root = Path(default_root) if default_root else Path(root_candidates[0])
    return final_root / typed_path, False


def ensure_config_file_exists_or_create_it(path: Optional[Path]) -> (Path, bool):
    path = path if path else Path("config.json")
    (final_path, exists) = existing_path_or_default(path,
                                                    root_candidates=[Path().cwd(),
                                                                     app_dirs.user_config_dir,
                                                                     Path().home()],
                                                    default_root=app_dirs.user_config_dir)
    if not exists:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        final_path.write_text("{}")

    return final_path, exists
