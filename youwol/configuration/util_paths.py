from pathlib import Path
from typing import Optional, Union, Callable, List

from appdirs import AppDirs

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
