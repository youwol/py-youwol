import asyncio
import json
import os
import shutil
from pathlib import Path
from typing import List, cast

import brotli
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from youwol.app.environment import (
    CdnSwitch,
    CloudEnvironment,
    CloudEnvironments,
    Command,
    Configuration,
    Connection,
    CustomEndPoints,
    Customization,
    CustomMiddleware,
    DirectAuth,
    FlowSwitcherMiddleware,
    IConfigurationFactory,
    LocalClients,
    LocalEnvironment,
    Projects,
    RemoteClients,
    System,
    YouwolEnvironment,
    get_standard_auth_provider,
)
from youwol.app.main_args import MainArguments
from youwol.app.routers.projects import ProjectLoader
from youwol.app.routers.system.router import LeafLogResponse, Log, NodeLogResponse
from youwol.pipelines.pipeline_typescript_weback_npm import (
    app_ts_webpack_template,
    lib_ts_webpack_template,
)
from youwol.utils import (
    ContextFactory,
    InMemoryReporter,
    execute_shell_cmd,
    parse_json,
    sed_inplace,
)
from youwol.utils.context import Context, Label

users = [
    (os.getenv("USERNAME_INTEGRATION_TESTS"), os.getenv("PASSWORD_INTEGRATION_TESTS")),
    (
        os.getenv("USERNAME_INTEGRATION_TESTS_BIS"),
        os.getenv("PASSWORD_INTEGRATION_TESTS_BIS"),
    ),
]

direct_auths = [
    DirectAuth(authId=email, userName=email, password=pwd) for email, pwd in users
]

cloud_env = CloudEnvironment(
    envId="prod",
    host="platform.int.youwol.com",
    authProvider=get_standard_auth_provider("platform.int.youwol.com"),
    authentications=direct_auths,
)


async def clone_project(git_url: str, branch: str, new_project_name: str, ctx: Context):
    folder_name = new_project_name.split("/")[-1]
    git_folder_name = git_url.split("/")[-1].split(".")[0]
    env = await ctx.get("env", YouwolEnvironment)
    parent_folder = env.pathsBook.config.parent / "projects"
    dst_folder = parent_folder / folder_name
    await execute_shell_cmd(
        cmd=f"(cd {parent_folder} && git clone -b {branch} {git_url})", context=ctx
    )
    if not (parent_folder / git_folder_name).exists():
        raise RuntimeError("Git repo not properly cloned")

    os.rename(parent_folder / git_folder_name, parent_folder / folder_name)
    old_project_name = parse_json(dst_folder / "package.json")["name"]
    sed_inplace(dst_folder / "package.json", old_project_name, new_project_name)
    sed_inplace(dst_folder / "index.html", old_project_name, new_project_name)
    return {}


async def purge_downloads(context: Context):
    async with context.start(
        action="purge_downloads", muted_http_errors={404}
    ) as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        assets_gtw = await RemoteClients.get_assets_gateway_client(
            remote_host=env.get_remote_info().host
        )
        headers = ctx.headers()
        default_drive = (
            await LocalClients.get_assets_gateway_client(env)
            .get_treedb_backend_router()
            .get_default_user_drive(headers=context.headers())
        )
        treedb_client = assets_gtw.get_treedb_backend_router()
        resp = await treedb_client.get_children(
            folder_id=default_drive["downloadFolderId"], headers=headers
        )
        await asyncio.gather(
            *[
                treedb_client.remove_item(item_id=item["treeId"], headers=headers)
                for item in resp["items"]
            ],
            *[
                treedb_client.remove_folder(folder_id=item["folderId"], headers=headers)
                for item in resp["folders"]
            ],
        )
        await treedb_client.purge_drive(
            drive_id=default_drive["driveId"], headers=headers
        )
        return {}


async def reset(ctx: Context):
    env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
    env.reset_cache()
    env.reset_databases()
    parent_folder = env.pathsBook.config.parent
    shutil.rmtree(parent_folder / "projects", ignore_errors=True)
    shutil.rmtree(parent_folder / "youwol_system", ignore_errors=True)
    os.mkdir(parent_folder / "projects")
    await ProjectLoader.initialize(env=env)


async def create_test_data_remote(context: Context):
    async with context.start("create_new_story_remote") as ctx:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        host = env.get_remote_info().host
        await ctx.info(f"selected Host for creation: {host}")
        folder_id = "private_51c42384-3582-494f-8c56-7405b01646ad_default-drive_home"
        gtw = await RemoteClients.get_assets_gateway_client(remote_host=host)
        asset_resp = await gtw.get_assets_backend_router().create_asset(
            body={
                "rawId": "test-custom-asset",
                "kind": "custom-asset",
                "name": "Asset + files (remote test data in local-youwol-client)",
                "description": "A custom asset used to test posting files and auto-download of assets with files",
                "tags": ["integration-test", "local-youwol-client"],
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )
        with open(Path(__file__).parent / "test-add-files.zip", "rb").read() as data:
            upload_resp = await gtw.get_assets_backend_router().add_zip_files(
                asset_id=asset_resp["assetId"], data=data, headers=ctx.headers()
            )

        resp_stories = await gtw.get_stories_backend_router().create_story(
            body={
                "storyId": "504039f7-a51f-403d-9672-577b846fdbd8",
                "title": "Story (remote test data in local-youwol-client)",
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )

        resp_flux = await gtw.get_flux_backend_router().create_project(
            body={
                "projectId": "2d5cafa9-f903-4fa7-b343-b49dfba20023",
                "description": "a flux project dedicated to test in http-clients",
                "name": "Flux-project (remote test data in local-youwol-client)",
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )

        content = json.dumps(
            {
                "description": "a file uploaded in remote env for test purposes (local-youwol-client)"
            }
        )
        form = {
            "file": str.encode(content),
            "content_type": "application/json",
            "file_id": "f72290f2-90bc-4192-80ca-20f983a1213d",
            "file_name": "Uploaded file (remote test data in local-youwol-client)",
        }
        resp_data = await gtw.get_files_backend_router().upload(
            data=form, params=[("folder-id", folder_id)], headers=ctx.headers()
        )
        resp = {
            "respCustomAsset": {"asset": asset_resp, "addFiles": upload_resp},
            "respStories": resp_stories,
            "respFlux": resp_flux,
            "respData": resp_data,
        }
        await ctx.info("Story successfully created", data=resp)
        return resp


async def erase_all_test_data_remote(context: Context):
    async with context.start("erase_all_test_data_remote") as ctx:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        host = env.get_remote_info().host
        await ctx.info(f"selected Host for deletion: {host}")
        drive_id = "private_51c42384-3582-494f-8c56-7405b01646ad_default-drive"
        folder_id = f"{drive_id}_home"
        gtw = await RemoteClients.get_assets_gateway_client(remote_host=host)
        resp = await gtw.get_treedb_backend_router().get_children(
            folder_id=folder_id, headers=ctx.headers()
        )
        await asyncio.gather(
            *[
                gtw.get_treedb_backend_router().remove_item(
                    item_id=item["itemId"], headers=ctx.headers()
                )
                for item in resp["items"]
            ]
        )
        await gtw.get_treedb_backend_router().purge_drive(
            drive_id=drive_id, headers=ctx.headers()
        )
        return {"items": resp["items"]}


pipeline_ts.set_environment()


def apply_test_labels_logs(body, _ctx):
    ContextFactory.add_labels(
        key="labels@local-yw-clients-tests", labels={body["file"], body["testName"]}
    )
    return {}


def retrieve_logs(body, context: Context):
    logger = cast(InMemoryReporter, context.logs_reporters[0])
    root_logs, nodes_logs, leaf_logs, errors = (
        logger.root_node_logs,
        logger.node_logs,
        logger.leaf_logs,
        logger.errors,
    )

    test_name = body["testName"]
    file_name = body["file"]
    nodes: List[Log] = [
        NodeLogResponse(
            **Log.from_log_entry(log).dict(), failed=log.context_id in errors
        )
        for log in root_logs + nodes_logs
        if test_name in log.labels and file_name in log.labels
    ]
    leafs: List[Log] = [
        LeafLogResponse(**Log.from_log_entry(log).dict())
        for log in leaf_logs
        if test_name in log.labels and file_name in log.labels
    ]

    return {
        "nodes": sorted(nodes, key=lambda n: n.timestamp),
        "leafs": sorted(leafs, key=lambda n: n.timestamp),
    }


async def test_command_post(body, context: Context):
    await context.info(text="test message", data={"body": body})
    return body["returnObject"]


class BrotliDecompressMiddleware(CustomMiddleware):
    async def dispatch(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ):
        async with context.start(
            action="BrotliDecompressMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context
            response = await call_next(incoming_request)
            if response.headers.get("content-encoding") != "br":
                return response
            await ctx.info(
                text="Got 'br' content-encoding => apply brotli decompression"
            )
            await context.info("Apply brotli decompression")
            binary = b""
            # noinspection PyUnresolvedReferences
            async for data in response.body_iterator:
                binary += data
            headers = {
                k: v
                for k, v in response.headers.items()
                if k not in ["content-length", "content-encoding"]
            }
            decompressed = brotli.decompress(binary)
            resp = Response(decompressed.decode("utf8"), headers=headers)
            return resp


class ConfigurationFactory(IConfigurationFactory):
    async def get(self, _main_args: MainArguments) -> Configuration:
        return Configuration(
            system=System(
                httpPort=2001,
                cloudEnvironments=CloudEnvironments(
                    defaultConnection=Connection(
                        envId="prod", authId=direct_auths[0].authId
                    ),
                    environments=[cloud_env],
                ),
                localEnvironment=LocalEnvironment(
                    dataDir=Path(__file__).parent / "databases",
                    cacheDir=Path(__file__).parent / "youwol_system",
                ),
            ),
            projects=Projects(
                finder=Path(__file__).parent,
                templates=[
                    lib_ts_webpack_template(folder=Path(__file__).parent / "projects"),
                    app_ts_webpack_template(folder=Path(__file__).parent / "projects"),
                ],
            ),
            customization=Customization(
                middlewares=[
                    FlowSwitcherMiddleware(
                        name="CDN live servers",
                        oneOf=[CdnSwitch(packageName="package-name", port=3006)],
                    ),
                    BrotliDecompressMiddleware(),
                ],
                endPoints=CustomEndPoints(
                    commands=[
                        Command(name="reset", do_get=reset),
                        Command(
                            name="clone-project",
                            do_post=lambda body, ctx: clone_project(
                                body["url"], body["branch"], body["name"], ctx
                            ),
                        ),
                        Command(
                            name="purge-downloads",
                            do_delete=purge_downloads,
                        ),
                        Command(
                            name="create-test-data-remote",
                            do_get=create_test_data_remote,
                        ),
                        Command(
                            name="erase_all_test_data_remote",
                            do_delete=erase_all_test_data_remote,
                        ),
                        Command(
                            name="test-cmd-post",
                            do_post=test_command_post,
                        ),
                        Command(
                            name="test-cmd-put",
                            do_put=lambda body, ctx: body["returnObject"],
                        ),
                        Command(
                            name="test-cmd-delete",
                            do_delete=lambda ctx: {"status": "deleted"},
                        ),
                        Command(
                            name="get-logs",
                            do_post=retrieve_logs,
                        ),
                        Command(
                            name="set-jest-context",
                            do_post=apply_test_labels_logs,
                        ),
                    ]
                ),
            ),
        )
