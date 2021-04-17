import os
from pathlib import Path
from typing import Dict

from youwol.utils_paths import ensure_folders
from youwol.configuration import (
    BackEnds, TargetBack, ConfigParameters, parameter_enum, FrontEnds, Packages,
    UserConfiguration, General, RemoteGateway, TargetFront,
    )
from youwol.main_args import MainArguments

from youwol.pipelines.fastapi.main import fast_api_pipeline
import youwol.pipelines.flux_pack.main as flux_pack
from youwol.pipelines.scribble_html.main import scribble_html_pipeline
import youwol.pipelines.library_webpack_ts.main as simple_ts_lib


async def configuration_parameters():
    return ConfigParameters(
        parameters={
            "bundleMode": parameter_enum(
                name="bundle mode",
                value="dev",
                values=["dev", "prod"],
                description="Mode to bundle npm package when applicable"
                )
            }
        )


async def configuration(main_args: MainArguments, parameters: Dict[str, any]):

    yw_config_path = Path("{{folder_path}}")

    data_path, workspace_path, system_path = ensure_folders(
        yw_config_path / "databases",
        yw_config_path / "workspace",
        yw_config_path / "youwol_system"
        )

    packages_path, flux_path = ensure_folders(
        workspace_path / "packages",
        workspace_path / "packages" / "flux"
        )

    backends_path, python_backs, fast_api_path = ensure_folders(
        workspace_path / "backends",
        workspace_path / "backends" / "python",
        workspace_path / "backends" / "python" / "fast-api"
        )

    frontends_path, scribble_path = ensure_folders(
        workspace_path / "frontends",
        workspace_path / "frontends" / "scribbles"
        )

    return UserConfiguration(
        general=General(
            databasesFolder=data_path,
            secretsFile=yw_config_path / "secrets.json",
            usersInfo=yw_config_path / "users-info.json",
            systemFolder=system_path,
            remoteGateways=[
                RemoteGateway(
                    name="dev.platform.youwol.com",
                    url="dev.platform.youwol.com"
                    )
                ],
            defaultPublishLocation="private/default-drive"
            ),
        packages=Packages(
            pipelines={
                "flux-pack": flux_pack.pipeline(
                    skeleton_path=flux_path,
                    mode=flux_pack.BundleModeEnum.PROD
                    if parameters["bundleMode"] == 'prod'
                    else flux_pack.BundleModeEnum.DEV
                    ),
                "simple-pack": simple_ts_lib.pipeline(
                    skeleton_path=packages_path,
                    mode=simple_ts_lib.BundleModeEnum.PROD
                    if parameters["bundleMode"] == 'prod'
                    else simple_ts_lib.BundleModeEnum.DEV
                    ),
                },
            targets={
                "flux-pack": flux_pack.get_targets(folder=flux_path),
                "simple-pack": simple_ts_lib.get_targets(folder=packages_path)
                }
            ),
        backends=BackEnds(
            pipelines={
                "fast-api": fast_api_pipeline(path=fast_api_path, conf="local")
                },
            targets={
                "fast-api": [TargetBack(folder=fast_api_path / f) for f in os.listdir(fast_api_path)
                             if (fast_api_path / f / 'src' / 'main.py').exists()]
                }
            ),
        frontends=FrontEnds(
            pipelines={
                "scratch-html": scribble_html_pipeline(path=scribble_path)
                },
            targets={
                "scratch-html": [TargetFront(folder=scribble_path / f) for f in os.listdir(scribble_path)
                                 if (scribble_path / f / 'index.html').exists()]
                }
            )
        )
