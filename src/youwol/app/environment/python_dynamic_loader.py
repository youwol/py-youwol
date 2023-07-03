# standard library
import importlib
import sys

from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path

# typing
from typing import List, Optional, Type, TypeVar, Union, cast

T = TypeVar("T")


def get_object_from_module(
    module_absolute_path: Path,
    object_or_class_name: str,
    object_type: Type[T],
    additional_src_absolute_paths: Optional[Union[Path, List[Path]]] = None,
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
            raise NameError(
                f"{module_absolute_path} : Expected class '{object_or_class_name}' not found"
            )

        maybe_class_or_var = getattr(imported_module, object_or_class_name)
        return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))
        # Need to be re-pluged ASAP. The problem is for now pipeline in 'yw_pipeline.py' use the deprecated
        # type youwol.app.environment.models.IPipelineFactory
        # Need to be replaced by:
        # youwol.app.routers.projects.models_projects.IPipelineFactory
        #
        # Below, original code:
        # if isinstance(maybe_class_or_var, object_type):
        #     return cast(object_type, maybe_class_or_var)
        #
        # if issubclass(maybe_class_or_var, object_type):
        #     return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))
        #
        # raise TypeError(f"{module_absolute_path} : Expected class '{object_or_class_name}'"
        #                 f" does not implements expected type '{object_type}")

    module_name = module_absolute_path.stem
    try:
        loader = SourceFileLoader(module_name, str(module_absolute_path))
        spec = spec_from_loader(module_name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        instance = get_instance_from_module(module)
    except SyntaxError as e:
        raise SyntaxError(f"{module_absolute_path} : Syntax error '{e}'")
    except NameError as e:
        raise NameError(e)

    return instance
