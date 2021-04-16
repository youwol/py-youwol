import os
import re
import shutil
import tempfile
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union, cast

from pydantic import BaseModel

from youwol.configuration import PipelineFront, BuildFront
from youwol.utils_low_level import to_json
from youwol.configuration.models_base import Skeleton, SkeletonParameter, Pipeline, Check, ErrorResponse

from youwol.context import Context, ActionStep, Action
from .checks import _check_app_name, _check_destination_folder


class BundleModeEnum(Enum):
    DEV = "DEV"
    PROD = "PROD"


class ScratchHtmlPipeline(PipelineFront):
    pass


def scribble_html_pipeline(path: Union[str, Path]):

    path = Path(path)

    return ScratchHtmlPipeline(
        skeleton=skeleton(path),
        build=BuildFront(
            run="",
            dist="./"
            ),
        )


description = """
A skeleton to scratch HTML/CSS/JS files for simple cases. For bigger projects, other pipelines should be used
(e.g typescript ones, angular, vue, etc)
"""


def skeleton(path: Union[str, Path]) -> Skeleton:
    return Skeleton(
        folder=path,
        description=description,
        parameters=[
            SkeletonParameter(
                id="name",
                displayName="Name",
                type='string',
                defaultValue=None,
                placeholder="Application name",
                description="name of the application",
                required=True
                ),
            SkeletonParameter(
                id="title",
                displayName="Title",
                type='string',
                defaultValue=None,
                placeholder="title",
                description="Page title",
                required=True
                )
            ],
        generate=generate
        )


class CreationStatus(BaseModel):

    validated: bool = False
    checks: List[Check]


class CheckDestinationFolder(Check):
    name: str = "Destination folder can be created?"


class CheckAppName(Check):
    name: str = "Package name is valid?"


async def generate(
        folder_path: Path,
        parameters: Dict[str, any],
        pipeline: Pipeline,
        context: Context
        ):
    check_destination_folder = CheckDestinationFolder()
    check_package_name = CheckAppName()
    pipeline = cast(ScratchHtmlPipeline, pipeline)

    async def check_status(ctx: Context):
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

    name = parameters["name"]
    title = parameters["title"]

    async with context.with_target(name).start(Action.INSTALL) as ctx:

        folder_name = name.split('/')[1] if '/' in name else name

        path_pack = folder_path/f"{folder_name}"

        await ctx.info(step=ActionStep.STATUS,
                       content=f"Start creation of skeleton",
                       json={'parameters': parameters,
                             'pathFolder': str(path_pack),
                             'pipeline': to_json(pipeline)
                             }
                       )
        _check_app_name(name, check_package_name)
        if check_package_name.status is not True:
            return None, await check_status(ctx)

        _check_destination_folder(path_pack, check_destination_folder)
        if check_destination_folder.status is not True:
            return None, await check_status(ctx)

        src_path = Path(__file__).parent / "files_template"
        shutil.copytree(src_path, path_pack)

        for subdir, dirs, files in os.walk(path_pack):
            for filename in files:
                try:
                    path = subdir + os.sep + filename
                    sed_inplace(path, "{{name}}", name)
                    sed_inplace(path, "{{base_path}}", f'/ui/{name}')
                    sed_inplace(path, "{{title}}", title)
                    sed_inplace(path, "{{src_folder}}", str(folder_path / name))
                except UnicodeError:
                    # Here when a file like python .pyc has been found (binary file, not 'sedable')
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
