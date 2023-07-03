# From the yw_config folder, run:
# python -m consistency_testing.main
# Following environment variables are required:
# USERNAME_INTEGRATION_TESTS PASSWORD_INTEGRATION_TESTS USERNAME_INTEGRATION_TESTS_BIS PASSWORD_INTEGRATION_TESTS_BIS
#
# standard library
import base64
import shutil

from pathlib import Path

# typing
from typing import List, cast

# third parties
import aiohttp

from fastapi import HTTPException

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.projects import get_project_configuration
from youwol.app.routers.projects.models_project import (
    Artifact,
    ExplicitNone,
    FileListing,
    FlowId,
    Link,
    LinkKind,
    PipelineStep,
    Project,
)
from youwol.app.routers.system.router import LeafLogResponse, Log, NodeLogResponse
from youwol.app.test.utils_test import PyYouwolSession, TestSession, py_youwol_session

# Youwol utilities
from youwol.utils import Context, ContextReporter, LogEntry, execute_shell_cmd

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.common import yarn_errors_formatter

# relative
from .common import Paths


class Reporter(ContextReporter):
    async def log(self, entry: LogEntry):
        if entry.text != "\n":
            print(entry.text.replace("\n", ""))


async def get_logs(session: PyYouwolSession, file: str, test: str):
    http_port = session.configuration.system.httpPort

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=f"http://localhost:{http_port}/admin/custom-commands/get-logs",
            json={"file": file, "testName": test},
        ) as resp:
            json_resp = await resp.json()
            nodes = cast(
                List[Log], [NodeLogResponse(**node) for node in json_resp["nodes"]]
            )
            leafs = cast(
                List[Log], [LeafLogResponse(**leaf) for leaf in json_resp["leafs"]]
            )
            return list(sorted(nodes + leafs, key=lambda n: n.timestamp))


class ConsistencyTestStep(PipelineStep):
    asset_raw_id = "consistency-testing"
    id: str

    run: ExplicitNone = ExplicitNone()
    sources: FileListing = FileListing(
        include=[Paths.package_json_file, Paths.lib_folder, "src/tests"],
        ignore=[
            Paths.auto_generated_file,
            "**/.*/*",
            "node_modules",
            "**/node_modules",
        ],
    )
    artifacts: List[Artifact] = [
        Artifact(
            id="consistency-results",
            files=FileListing(
                include=["consistency-testing"],
            ),
            links=[
                Link(
                    name="report",
                    url=f"/applications/@youwol/logs-explorer/latest?"
                    f"id={base64.b64encode(asset_raw_id.encode('ascii')).decode()}",
                    kind=LinkKind.plainUrl,
                )
            ],
        )
    ]
    view: str = Path(__file__).parent / "views" / "consistency.view.js"

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        async with context.start(
            action="run ConsistencyTestStep.execute_run", with_reporters=[Reporter()]
        ) as ctx:
            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            count = config["count"]
            results_folder = Path(f"{project.path}/consistency-testing")
            if results_folder.exists():
                shutil.rmtree(
                    results_folder,
                )
            await self._delete_asset(context=ctx)
            consistency_testing = TestSession(
                result_folder=results_folder, raw_id=self.asset_raw_id
            )
            for i in range(count):
                async with ctx.start(
                    action=f"Start run #{i}"
                ) as ctx_run:  # type: Context
                    # Environment variables required by the following conf must be maid available
                    async with py_youwol_session(
                        config_path=config["configPath"],
                        context=ctx_run,
                    ) as py_yw_session:
                        await consistency_testing.execute(
                            py_yw_session=py_yw_session,
                            title="yarn test",
                            action=lambda ctx_action: execute_shell_cmd(
                                cmd=f"(cd {project.path} && yarn test )",
                                context=ctx_action,
                            ),
                            errors_formatter=yarn_errors_formatter,
                            py_yw_logs_getter=get_logs,
                            context=ctx_run,
                        )

    async def _delete_asset(self, context: Context):
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        explorer_client = LocalClients.get_assets_gateway_client(
            env
        ).get_treedb_backend_router()
        asset_id = base64.b64encode(self.asset_raw_id.encode("ascii")).decode()
        try:
            resp = await explorer_client.get_item(
                item_id=asset_id, headers=context.headers()
            )
        except HTTPException as e:
            if e.status_code == 404:
                return
            raise e

        await explorer_client.remove_item(item_id=asset_id, headers=context.headers())
        await explorer_client.purge_drive(
            drive_id=resp["driveId"], headers=context.headers()
        )
