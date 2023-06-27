# From the yw_config folder, run:
# python -m consistency_testing.main
# Following environment variables are required:
# USERNAME_INTEGRATION_TESTS PASSWORD_INTEGRATION_TESTS USERNAME_INTEGRATION_TESTS_BIS PASSWORD_INTEGRATION_TESTS_BIS
#
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import cast, List

import aiohttp

from youwol.pipelines.pipeline_typescript_weback_npm import yarn_errors_formatter
from youwol.app.routers.system.router import Log, NodeLogResponse, LeafLogResponse
from youwol.utils import execute_shell_cmd, ContextReporter, LogEntry, Context
from youwol.utils.utils_test import (
    TestSession,
    Publication,
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


async def execute():
    count = 100

    consistency_testing = TestSession(
        result_folder=Path(f"./test_stability_{datetime.now()}"),
        publication=Publication(
            remote_host="platform.youwol.com",
            client_id=os.getenv("USERNAME_INTEGRATION_TESTS"),
            client_secret=os.getenv("PASSWORD_INTEGRATION_TESTS"),
        ),
    )
    for _ in range(count):
        async with py_youwol_session(config_path="./yw_config.py") as py_yw_session:
            await consistency_testing.execute(
                py_yw_session=py_yw_session,
                title="yarn test",
                action=lambda: execute_shell_cmd(
                    cmd="(cd ../.. & yarn test )", context=context
                ),
                errors_formatter=yarn_errors_formatter,
                py_yw_logs_getter=get_logs,
            )


asyncio.run(execute())
