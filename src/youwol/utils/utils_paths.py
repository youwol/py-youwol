# standard library
import glob
import hashlib
import itertools
import json
import os
import re
import shutil
import tempfile
import zipfile

from collections.abc import Iterable
from fnmatch import fnmatch
from os import PathLike
from pathlib import Path

# typing
from typing import IO, Callable, Optional, Union, cast

# third parties
import aiohttp
import yaml

from pydantic import BaseModel

# relative
from .utils import JSON


class FileListing(BaseModel):
    include: list[str]
    ignore: list[str] = []


flatten = itertools.chain.from_iterable


def list_files(folder: Path, rec=True) -> list[Path]:
    return [
        Path(p)
        for p in glob.glob(str(folder) + "/**/*", recursive=rec)
        if Path(p).is_file()
    ]


def parse_json(path: Union[str, Path]):
    return json.load(open(str(path), encoding="UTF-8"))


def parse_yaml(path: Union[str, Path]):
    with open(path, encoding="UTF-8") as stream:
        return yaml.safe_load(stream)


def write_json(data: JSON, path: Path):
    with open(path, "w", encoding="UTF-8") as fp:
        json.dump(data, fp, indent=4)


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


def matching_files(
    folder: Union[Path, str], patterns: Union[list[str], FileListing]
) -> list[Path]:
    folder = Path(folder)

    def fix_pattern(pattern):
        if (folder / pattern).is_dir():
            return [pattern + "/**/*", pattern + "/*"]
        return [pattern]

    patterns = (
        FileListing(include=patterns, ignore=[])
        if isinstance(patterns, list)
        else patterns
    )
    patterns = FileListing(
        include=list(flatten([fix_pattern(p) for p in patterns.include])),
        ignore=patterns.ignore,
    )
    patterns_folder_ignore = patterns.ignore

    def is_selected(filepath: Path):
        if any(fnmatch(str(filepath), pattern) for pattern in patterns.ignore):
            return False
        return any(fnmatch(str(filepath), pattern) for pattern in patterns.include)

    def to_skip_branch(path: Path):
        return any(fnmatch(str(path), pattern) for pattern in patterns_folder_ignore)

    selected: list[Path] = []
    for root, dirs, files in os.walk(folder):
        root_path = Path(root)
        relative_root_path = root_path.relative_to(folder)
        if to_skip_branch(relative_root_path):
            dirs[:] = []
            continue
        selected = selected + [
            root_path / f for f in files if is_selected(relative_root_path / f)
        ]

    return selected


def ensure_folders(*paths: Union[str, Path]):
    r = []
    for path in paths:
        p = Path(path)
        os.makedirs(p, exist_ok=True)
        r.append(p)
    return r


def files_check_sum(paths: Iterable[Union[str, Path]]):
    def md5_update_from_file(filename: Union[str, Path], current_hash):
        with open(str(filename), "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                current_hash.update(chunk)
        return current_hash

    sha_hash = hashlib.md5()

    for path in sorted(paths, key=lambda p: str(p).lower()):
        sha_hash.update(str(path).encode())
        sha_hash = md5_update_from_file(path, sha_hash)
    return sha_hash.hexdigest()


def create_zip_file(
    path: Path,
    files_to_zip: list[tuple[Path, str]],
    with_data: Optional[list[tuple[str, Union[str, bytes]]]] = None,
):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zipper:
        for path_file, name in files_to_zip:
            zipper.write(filename=path_file, arcname=name)
        if with_data:
            for arc_name, raw in with_data:
                zipper.writestr(arc_name, data=raw)


class PathException(RuntimeError):
    path: str


def default_create_dir(final_path: Path):
    try:
        final_path.mkdir(parents=True)
    except Exception as e:
        raise PathException(f"Error while creating '{str(final_path)}' : {e}")


def fail_on_missing_dir(path: Path):
    raise PathException(f"Not creating missing dir '{str(path)}'")


def do_nothing_on_missing_dir(_path: Path):
    # Do nothing, but do it well
    pass


def ensure_dir_exists(
    path: Optional[Union[str, Path]],
    root_candidates: Union[Union[str, Path], list[Union[str, Path]]],
    default_root: Optional[Union[str, Path]] = None,
    create: Callable[[Path], None] = default_create_dir,
) -> Path:
    path = path if path else "."
    (final_path, exists) = existing_path_or_default(
        path, root_candidates=root_candidates, default_root=default_root
    )

    if exists:
        if not final_path.is_dir():
            raise PathException(f"'{str(final_path)}' is not a directory")
    else:
        create(final_path)

    return final_path


def ensure_file_exists(
    path: Union[str, Path],
    root_candidates: Union[Union[str, Path], list[Union[str, Path]]],
    default_root: Optional[Union[str, Path]] = None,
    default_content: Optional[str] = None,
) -> Path:
    (final_path, exists) = existing_path_or_default(
        path, root_candidates=root_candidates, default_root=default_root
    )

    if exists:
        if not final_path.is_file():
            raise PathException(f"'{str(final_path)}' is not a file")
    else:
        if default_content:
            try:
                final_path.parent.mkdir(parents=True, exist_ok=True)
                final_path.write_text(default_content, encoding="UTF-8")
            except Exception as e:
                raise PathException(f"Error while creating '{str(final_path)}' : {e}")
        else:
            raise PathException(f"'{str(final_path)}' does not exist")

    return final_path


def existing_path_or_default(
    path: Union[str, Path],
    root_candidates: Union[Union[str, Path], list[Union[str, Path]]],
    default_root: Optional[Union[str, Path]] = None,
) -> tuple[Path, bool]:
    typed_path = Path(path)

    if typed_path.is_absolute():
        return typed_path, typed_path.exists()

    if not isinstance(root_candidates, list):
        root_candidates = [root_candidates]

    root_candidates_idx = 0
    while root_candidates_idx < len(root_candidates):
        absolute_path = Path(root_candidates[root_candidates_idx]) / typed_path
        if absolute_path.exists():
            return absolute_path, True
        root_candidates_idx = root_candidates_idx + 1

    final_root = Path(default_root) if default_root else Path(root_candidates[0])
    return final_root / typed_path, False


async def get_databases_path(pyyouwol_port):
    async with aiohttp.ClientSession() as session:
        async with await session.get(
            url=f"http://localhost:{pyyouwol_port}/admin/environment/status"
        ) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                return Path(json_resp["configuration"]["pathsBook"]["databases"])


async def get_running_py_youwol_env(py_youwol_port):
    async with aiohttp.ClientSession() as session:
        async with await session.get(
            url=f"http://localhost:{py_youwol_port}/admin/environment/status"
        ) as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                return json_resp["configuration"]


def extract_zip_file(
    file: IO,
    zip_path: Union[Path, str],
    dir_path: Union[Path, str],
    delete_original=True,
):
    dir_path = str(dir_path)
    with open(zip_path, "ab") as f:
        for chunk in iter(lambda: file.read(10000), b""):
            f.write(chunk)

    compressed_size = Path(zip_path).stat().st_size

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dir_path)

    if delete_original:
        os.remove(zip_path)

    return compressed_size


def sed_inplace(filename, pattern, repl):
    # Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
    # `sed -i -e 's/'${pattern}'/'${repl}' ${filename}"`.

    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        with open(filename, encoding="UTF-8") as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)
