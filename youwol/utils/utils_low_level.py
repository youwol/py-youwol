import importlib
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import spec_from_loader
from pathlib import Path
from typing import Union, List, Type, cast, TypeVar, Optional

from aiohttp import ClientSession, TCPConnector
from starlette.requests import Request
from starlette.responses import Response
from youwol_utils import assert_response


async def redirect_request(
        incoming_request: Request,
        origin_base_path: str,
        destination_base_path: str,
        headers=None
        ):
    rest_of_path = incoming_request.url.path.split(origin_base_path)[1].strip('/')
    headers = {k: v for k, v in incoming_request.headers.items()} if not headers else headers
    redirect_url = f"{destination_base_path}/{rest_of_path}"

    async def forward_response(response):
        await assert_response(response)
        headers_resp = {k: v for k, v in response.headers.items()}
        content = await response.read()
        return Response(status_code=response.status, content=content, headers=headers_resp)

    params = incoming_request.query_params
    # after this eventual call, a subsequent call to 'body()' will hang forever
    data = await incoming_request.body() if incoming_request.method in ['POST', 'PUT', 'DELETE'] else None

    async with ClientSession(connector=TCPConnector(verify_ssl=False), auto_decompress=False) as session:

        if incoming_request.method == 'GET':
            async with await session.get(url=redirect_url, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'POST':
            async with await session.post(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'PUT':
            async with await session.put(url=redirect_url, data=data, params=params, headers=headers) as resp:
                return await forward_response(resp)

        if incoming_request.method == 'DELETE':
            async with await session.delete(url=redirect_url, data=data,  params=params, headers=headers) as resp:
                return await forward_response(resp)


T = TypeVar('T')


def get_object_from_module(
        module_absolute_path: Path,
        object_or_class_name: str,
        object_type: Type[T],
        additional_src_absolute_paths: Optional[Union[Path, List[Path]]] = None,
        **object_instantiation_kwargs
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
            raise NameError(f"{module_absolute_path} : Expected class '{object_or_class_name}' not found")

        maybe_class_or_var = imported_module.__getattribute__(object_or_class_name)
        return cast(object_type, maybe_class_or_var(**object_instantiation_kwargs))
        # Need to be re-pluged ASAP. The problem is for now pipeline use deprecated
        # type youwol.environment.models.IPipelineFactory
        # Need to replace in yw_pipeline.py
        # from youwol.environment.models import IPipelineFactory
        # by
        # from youwol.environment.models_projects  import IPipelineFactory
        # Original code:
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
        raise NameError(f"{module_absolute_path} :Name error '{e}")

    return instance
