import functools
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel

from .checks import _check_name, _check_destination_folder
from youwol.configuration.models_back import PipelineBack, InstallBack, ServeBack, TargetBack, BackEnd
from youwol.configuration.models_base import Skeleton, SkeletonParameter, Pipeline, Check, ErrorResponse

from youwol.context import Context, ActionStep, Action
from youwol.routers.packages.models import Package


class FastApiPipeline(PipelineBack):
    servingMode: str = "local"


def fast_api_pipeline(path: Union[str, Path], conf: str):

    path = Path(path)

    def is_installed(package: Package, _context: Context):
        return (Path(package.target.folder)/'scripts'/'.virtualenv').exists()

    def run(backend: BackEnd, context: Context):
        port = backend.info.port
        cmd = f"./serve --conf=local --port={port} --gateway=http://localhost:{context.config.http_port}"
        return cmd

    def open_api(backend: BackEnd, context: Context):
        return f"/api/{backend.info.name}/docs"

    if not path.exists():
        os.makedirs(path, exist_ok=True)

    return FastApiPipeline(
        servingMode=conf,
        skeleton=skeleton(path),
        install=InstallBack(
            run="./setup",
            isInstalled=is_installed
            ),
        serve=ServeBack(
            run=run,
            health="/healthz",
            openApi=open_api
            )
        )


def fast_api_targets(path: Union[str, Path]) -> List[TargetBack]:
    path = Path(path)
    if not path / 'mappings.json':
        return []
    path = path / 'mappings.json'
    mappings = json.loads(path.read_text())['mappings']
    return [TargetBack(**mapping) for mapping in mappings]


def skeleton(path: str) -> Skeleton:
    return Skeleton(
        folder=path,
        description="A skeleton to create a fastapi based backend service.",
        parameters=[
            SkeletonParameter(
                id="service-name",
                displayName="Name",
                type='string',
                defaultValue=None,
                placeholder="Service name",
                description=
                "Name of the service. Only '-' and '_' allowed as punctuation.",
                required=True
                ),
            SkeletonParameter(
                id="service-description",
                displayName="Description",
                type='text',
                defaultValue="",
                placeholder="You can provide a short description of your service here",
                description="Description that will be included in documentations.",
                required=False
                )
            ],
        generate=generate
        )


class CreationStatus(BaseModel):

    validated: bool = False
    checks: List[Check]


class CheckName(Check):
    name: str = "Package name is not valid"


class CheckDestinationFolder(Check):
    name: str = "Destination folder can not be created"


async def generate(
        folder_path: Path,
        parameters: Dict[str, any],
        pipeline: Pipeline,
        context: Context
        ):
    check_destination_folder = CheckDestinationFolder()
    check_package_name = CheckName()

    async def get_status(ctx: Context):
        checks = [
                check_package_name,
                check_destination_folder
                ]
        failed = [c.dict() for c in checks if isinstance(c.status, ErrorResponse)]
        if failed:
            await ctx.abort(
                content=f"Installation of the skeleton failed: " + failed[0]['status']['reason'],
                json={'failedChecks': failed,
                      'allChecks': [c.dict() for c in checks]
                      }
                )
        return CreationStatus(
            validated=len(failed) == 0,
            checks=checks
            )

    name = parameters["service-name"]
    description = parameters["service-description"]

    async with context.with_target(name).start(Action.INSTALL) as ctx:

        path_folder = folder_path / name

        await ctx.info(step=ActionStep.STATUS,
                       content=f"Start creation of skeleton",
                       json={'parameters': parameters,
                             'pathFolder': str(path_folder)
                             }
                       )
        _check_name(name, check_package_name)
        if check_package_name.status is not True:
            return None, await get_status(ctx)

        _check_destination_folder(path_folder, check_destination_folder)
        if check_destination_folder.status is not True:
            return None, await get_status(ctx)

        src_path = Path(__file__).parent / "files_template"
        shutil.copytree(src_path, path_folder)
        port = 2000 + functools.reduce(lambda acc, e: acc + ord(e), name, 0) % 1000
        for subdir, dirs, files in os.walk(path_folder):
            for filename in files:
                try:
                    path = subdir + os.sep + filename
                    sed_inplace(path, "{{name}}", name)
                    sed_inplace(path, "{{description}}", description)
                    sed_inplace(path, "{{display_name}}", name)
                    sed_inplace(path, "{{basePath}}", f"/api/{name}")
                    sed_inplace(path, "{{author}}", context.config.userEmail.split("@")[0])
                    sed_inplace(path, "{{email}}", context.config.userEmail)
                    sed_inplace(path, "{{conf}}", 'local')
                    sed_inplace(path, "{{port}}", str(port))
                    sed_inplace(path, "{{gateway}}", f"http://localhost:{context.config.http_port}")
                except UnicodeError:
                    # Here when a file like python pyc has been found (binary file, not 'sedable')
                    pass


def sed_inplace(filename, pattern, repl):
    """"
    Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
    `sed -i -e 's/'${pattern}'/'${repl}' "${filename}"`.
    """
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)
