# standard library
import importlib
import sys
import traceback as tb

from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path

# typing
from typing import Optional, TypeVar, Union, cast

T = TypeVar("T")


class ModuleLoadingException(Exception):
    path: str
    traceback: str
    exception_type: str

    def __init__(self, message, path, traceback, exception_type):
        super().__init__(message)
        self.path = path
        self.traceback = traceback
        self.exception_type = exception_type


def get_object_from_module(
    module_absolute_path: Path,
    object_or_class_name: str,
    object_type: type[T],
    additional_src_absolute_paths: Optional[Union[Path, list[Path]]] = None,
    **object_instantiation_kwargs,
) -> T:
    if additional_src_absolute_paths is None:
        additional_src_absolute_paths = []

    if isinstance(additional_src_absolute_paths, Path):
        additional_src_absolute_paths = [additional_src_absolute_paths]

    for path in additional_src_absolute_paths:
        if path not in sys.path:
            sys.path.append(str(path))

    def get_instance_from_module(imported_module):
        if not hasattr(imported_module, object_or_class_name):
            raise ModuleLoadingException(
                path=str(module_absolute_path),
                message=f"Expected class '{object_or_class_name}' not found",
                traceback=tb.format_exc(),
                exception_type="NameError",
            )

        maybe_class_or_var = getattr(imported_module, object_or_class_name)
        if isinstance(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var)

        if issubclass(maybe_class_or_var, object_type):
            return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))

        raise ModuleLoadingException(
            path=str(module_absolute_path),
            message=f"'{object_or_class_name}' does not implement '{object_type}'",
            traceback=tb.format_exc(),
            exception_type="NameError",
        )

    module_name = module_absolute_path.stem
    try:
        loader = SourceFileLoader(module_name, str(module_absolute_path))
        spec = spec_from_loader(module_name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        instance = get_instance_from_module(module)
    except Exception as e:
        raise ModuleLoadingException(
            path=str(module_absolute_path),
            message=str(e),
            traceback=tb.format_exc(),
            exception_type=type(e).__name__,
        )

    return instance
