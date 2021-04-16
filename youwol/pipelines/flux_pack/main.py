import os
import re
import shutil
import tempfile
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel

from youwol.utils_paths import get_targets_generic
from .checks import _check_package_name, _check_destination_folder
from youwol.configuration.models_base import Skeleton, SkeletonParameter, FileListing, Pipeline, Check, ErrorResponse
from youwol.configuration.models_package import (
    InstallPackage, BuildPackage, TestPackage, CDNPackage,
    PipelinePackage, TargetPackage,
    )
from youwol.context import Context, ActionStep, Action
from youwol.routers.packages.models import Package


class BundleModeEnum(Enum):
    DEV = "DEV"
    PROD = "PROD"


class FluxPipeline(PipelinePackage):
    mode: BundleModeEnum


def pipeline(
        skeleton_path: Union[str, Path],
        mode: BundleModeEnum,
        source_node_modules: Path = None,
        destination_node_modules: List[Path] = None
        ):

    def is_installed(package: Package, _context: Context):
        return (Path(package.target.folder) / 'node_modules').exists()

    def documentation_link(target: Package):
        base_path = target.cdn_base_path()
        return f"{base_path}/dist/docs/index.html"

    return FluxPipeline(
        mode=mode,
        skeleton=skeleton(Path(skeleton_path)),
        documentation=documentation_link,
        install=InstallPackage(
            run="yarn",
            isInstalled=is_installed
            ),
        build=BuildPackage(
            run=f"yarn build:{mode.name.lower()} && yarn doc",
            sourceNodeModules=source_node_modules,
            destinationNodeModules=destination_node_modules,
            checkSum=FileListing(
                include=["package.json", "src", "docs"],
                ignore=["**/test-drive/*", "**/auto_generated.ts"]
                )
            ),
        test=TestPackage(
            run="yarn test"
            ),
        cdn=CDNPackage(
            targets=FileListing(
                include=["*", "**/*"],
                ignore=["src", "dist/esm5", "dist/esm2015", "dist/fesm5", "dist/fesm2015", "dist/lib",
                        "**/*.d.ts", "ng-package.json", "tslint.json", "tsconfig.lib.json"]
                )
            )
        )


description = """
A skeleton to create modules box for YouWol. This will generate a minimal working versions, 
Please refer to the readme.md file of the created package for help to go further.
"""
description_flux_pack_name = """The package name used in the package.json file. It is recommended to use a namespace 
from your organisation or name (e.g. '@my-organization/my-lib')
"""


def skeleton(path: Union[str, Path]) -> Skeleton:
    return Skeleton(
        folder=path,
        description=description,
        parameters=[
            SkeletonParameter(
                id="flux-pack-name",
                displayName="Name",
                type='string',
                defaultValue=None,
                placeholder="Package name",
                description=description_flux_pack_name,
                required=True
                ),
            SkeletonParameter(
                id="flux-pack-description",
                displayName="Description",
                type='text',
                defaultValue="",
                placeholder="Description of your package",
                description="""The description of your package.""",
                required=False
                )
            ],
        generate=generate
        )


class CreationStatus(BaseModel):

    validated: bool = False
    checks: List[Check]


class CheckPackageName(Check):
    name: str = "Package name is not valid"


class CheckDestinationFolder(Check):
    name: str = "Destination folder can not be created"


def get_targets(folder:  Union[str, Path]):
    return get_targets_generic(folder, "yw_pipeline_flux_pack", TargetPackage)


async def generate(
        folder_path: Path,
        parameters: Dict[str, any],
        pipeline: Pipeline,
        context: Context
        ):
    check_destination_folder = CheckDestinationFolder()
    check_package_name = CheckPackageName()

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

    name = parameters["flux-pack-name"]

    async with context.with_target(name).start(Action.INSTALL) as ctx:

        folder_name = name.split('/')[1] if '/' in name else name

        path_pack = folder_path/f"{folder_name}"

        await ctx.info(step=ActionStep.STATUS,
                       content=f"Start creation of skeleton",
                       json={'parameters': parameters,
                             'pathFolder': str(path_pack)
                             }
                       )
        _check_package_name(name, check_package_name)
        if check_package_name.status is not True:
            return None, await get_status(ctx)

        _check_destination_folder(path_pack, check_destination_folder)
        if check_destination_folder.status is not True:
            return None, await get_status(ctx)

        src_path = Path(__file__).parent / "files_template"
        shutil.copytree(src_path, path_pack)

        for subdir, dirs, files in os.walk(path_pack):
            for filename in files:
                try:
                    path = subdir + os.sep + filename
                    sed_inplace(path, "{{name}}", name)
                    sed_inplace(path, "{{description}}", "")
                    sed_inplace(path, "{{display_name}}", name)
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
