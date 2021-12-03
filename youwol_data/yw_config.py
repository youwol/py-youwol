from typing import Dict
from fastapi import APIRouter

from configuration import Packages
from utils_paths import ensure_folders, get_targets
from youwol.configuration.models_base import ConfigParameters, parameter_enum
from youwol.configuration.user_configuration import UserConfiguration, General
from youwol.main_args import MainArguments

import youwol.pipelines.library_webpack_ts.main as npm_package
import youwol.pipelines.flux_pack.main as flux_pack


async def configuration_parameters():
    return ConfigParameters(
        parameters={
            "bundleMode": parameter_enum(
                name="bundle mode",
                value="prod",
                values=["dev", "prod"],
                description="Mode to bundle npm package when applicable"
                )
            }
        )


async def configuration(_main_args: MainArguments, parameters: Dict[str, any]):

    config_dir = _main_args.config_path.parent
    data_path = config_dir
    projects_path, databases_path, youwol_system_path = ensure_folders(
        data_path / "projects",
        data_path / "databases",
        data_path / "youwol_system"
        )
    return UserConfiguration(
        general=General(
            databasesFolder=databases_path,
            systemFolder=youwol_system_path,
            remotesInfo=config_dir / "remotes-info.json",
            usersInfo=config_dir / "users-info.json",
            secretsFile=config_dir / "secrets.json",
            openid_host="gc.auth.youwol.com"
            ),
        packages=Packages(
            pipelines={
                "npm-package": npm_package.pipeline(
                    skeleton_path=projects_path,
                    mode=npm_package.BundleModeEnum.PROD if parameters["bundleMode"] == 'prod' else
                    npm_package.BundleModeEnum.DEV
                    ),
                "flux-pack": flux_pack.pipeline(
                    skeleton_path=projects_path,
                    mode=flux_pack.BundleModeEnum.PROD if parameters["bundleMode"] == 'prod' else
                    flux_pack.BundleModeEnum.DEV
                    ),
                },
            targets={
                "npm-package": get_targets(
                    folders=[projects_path],
                    pipeline_name='yw_pipeline_webpack_ts'),
                "flux-pack": get_targets(
                    folders=[projects_path],
                    pipeline_name='yw_pipeline_flux_pack')
                }
            )
        )

router = APIRouter()
