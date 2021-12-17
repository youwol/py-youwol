import glob
import hashlib
import itertools
import json
import os
import shutil
from fnmatch import fnmatch
from os import PathLike
from pathlib import Path
from typing import cast, Union, List, Set, Iterable
from pydantic import BaseModel


class FileListing(BaseModel):
    include: List[str]
    ignore: List[str] = []


flatten = itertools.chain.from_iterable


def list_files(folder: Path, rec=True) -> List[Path]:
    return [Path(p) for p in glob.glob(str(folder)+'/**/*', recursive=rec) if Path(p).is_file()]


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


def files_check_sum(paths: Iterable[Union[str, Path]]):

    def md5_update_from_file(
            filename: Union[str, Path],
            current_hash):
        with open(str(filename), "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                current_hash.update(chunk)
        return current_hash

    sha_hash = hashlib.md5()

    for path in sorted(paths, key=lambda p: str(p).lower()):
        sha_hash.update(str(path).encode())
        sha_hash = md5_update_from_file(path, sha_hash)
    sha_hash = sha_hash.hexdigest()
    return sha_hash
