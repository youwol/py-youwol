import itertools
import json
import os
import shutil
from fnmatch import fnmatch
from json import JSONDecodeError
from os import PathLike
from pathlib import Path
from typing import cast, Union, List, Set

from youwol.configuration import TargetPackage
from youwol.configuration.models_base import FileListing


flatten = itertools.chain.from_iterable


def copy_tree(source: Path, destination: Path, replace: bool = False):
    # An helper to not having to cast stuffs all the time. See https://youtrack.jetbrains.com/issue/PY-30747
    if replace and os.path.exists(destination):
        shutil.rmtree(destination)
    shutil.copytree(cast(PathLike, source), cast(PathLike, destination))


def copy_file(source: Path, destination: Path, create_folders: bool = False):

    if create_folders and not destination.parent.exists():
        os.makedirs(destination.parent)
    # An helper to not having to cast stuffs all the time. See https://youtrack.jetbrains.com/issue/PY-30747
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
        if any(fnmatch(filepath, pattern) for pattern in patterns.ignore):
            return False
        return any(fnmatch(filepath, pattern) for pattern in patterns.include)

    def to_skip_branch(path: Path):
        if str(path) == ".":
            return False
        if any(fnmatch(path, pattern) for pattern in patterns_folder_ignore):
            return True
        if any(fnmatch(path, pattern)for pattern in patterns_folder_include):
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


def get_targets(folders: List[Union[str, Path]], pipeline_name: str, target_type: type = TargetPackage):

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
            print("Failed to decode package.json: "+folder/f/'package.json')
            continue

        if 'youwol' in package_json and \
                "pipeline" in package_json['youwol'] and \
                package_json['youwol']["pipeline"]["name"] == pipeline_name:
            targets.append(target_type(folder=folder/f))

    return targets
