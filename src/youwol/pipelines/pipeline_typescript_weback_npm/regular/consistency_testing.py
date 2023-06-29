# From the yw_config folder, run:
# python -m consistency_testing.main
# Following environment variables are required:
# USERNAME_INTEGRATION_TESTS PASSWORD_INTEGRATION_TESTS USERNAME_INTEGRATION_TESTS_BIS PASSWORD_INTEGRATION_TESTS_BIS
#
import base64

import shutil

from pathlib import Path
from typing import cast, List

import aiohttp

from youwol.app.routers.projects.models_project import (
    FileListing,
    PipelineStep,
    Project,
    FlowId,
    ExplicitNone,
    Artifact,
    Link,
    LinkKind,
)

from youwol.app.routers.system.router import Log, NodeLogResponse, LeafLogResponse
from .common import Paths
from youwol.pipelines.pipeline_typescript_weback_npm.common import yarn_errors_formatter
from youwol.utils import (
    execute_shell_cmd,
    ContextReporter,
    LogEntry,
    Context,
)
from youwol.app.test.utils_test import (
    TestSession,
    py_youwol_session,
    PyYouwolSession,
)


class Reporter(ContextReporter):
    async def log(self, entry: LogEntry):
        if entry.text != "\n":
            print(entry.text.replace("\n", ""))


context = Context(logs_reporters=[Reporter()], data_reporters=[])


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

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        async with context.start(
            action="run ConsistencyTestStep.execute_run", with_reporters=[Reporter()]
        ) as ctx:
            # count = 2 while WIP, will be retrieved from a configuration's view
            count = 2
            results_folder = Path(f"{project.path}/consistency-testing")
            if results_folder.exists():
                shutil.rmtree(
                    results_folder,
                )
            consistency_testing = TestSession(
                result_folder=results_folder, raw_id=self.asset_raw_id
            )
            for i in range(count):
                async with ctx.start(
                    action=f"Start run #{i}"
                ) as ctx_run:  # type: Context
                    # Environment variables required by the following conf must be maid available
                    async with py_youwol_session(
                        # config_path hard coded while WIP, will be retrieved from a configuration's view
                        config_path="/home/greinisch/Projects/youwol-open-source/python/py-youwol/integrations/yw_config.py",
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
