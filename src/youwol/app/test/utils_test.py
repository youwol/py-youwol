# standard library
import asyncio
import shutil
import tempfile
import time
import uuid
import zipfile

from contextlib import asynccontextmanager
from datetime import datetime
from http.client import HTTPException
from pathlib import Path
from signal import SIGKILL

# typing
from typing import (
    AsyncContextManager,
    Awaitable,
    Callable,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

# third parties
import psutil

from colorama import Fore, Style
from colorama import init as colorama_init
from psutil import process_iter
from websockets.exceptions import InvalidMessage
from websockets.legacy.client import connect as ws_connect

# Youwol
import youwol

# Youwol application
from youwol.app.environment import (
    Configuration,
    LocalClients,
    YouwolEnvironment,
    configuration_from_python,
)
from youwol.app.middlewares import get_connected_local_tokens
from youwol.app.routers.system.router import Log

# Youwol utilities
from youwol.utils import Context, execute_shell_cmd, parse_json, write_json

colorama_init()


no_log_context = Context(logs_reporters=[], data_reporters=[])


async def wait_py_youwol_ready(port: int, context: Context):
    async def handler(websocket):
        await websocket.recv()

    count = 1
    while True:
        await asyncio.sleep(1)
        await context.info(f"Try ping #{count}")
        try:
            async with ws_connect(f"ws://localhost:{port}/ws-data") as ws:
                await handler(ws)
            break
        except (ConnectionResetError, ConnectionRefusedError, InvalidMessage):
            count = count + 1
            if count > 9:
                raise RuntimeError(
                    f"Can not connect to py-youwol on port {port} after {count}s"
                )


def stop_py_youwol(port: int):
    for proc in process_iter():
        try:
            for conns in proc.connections(kind="inet"):
                if conns.laddr.port == port:
                    proc.send_signal(SIGKILL)  # or SIGKILL
        except (PermissionError, psutil.AccessDenied):
            pass


class PyYouwolSession(NamedTuple):
    configuration: Configuration


@asynccontextmanager
async def py_youwol_session(
    config_path: Union[Path, str], context: Context
) -> AsyncContextManager[PyYouwolSession]:
    async with context.start(action="Start py-youwol session") as ctx:  # Type: Context
        await ctx.info(f"Use config file {config_path}")
        config = await configuration_from_python(Path(config_path))
        port = config.system.httpPort

        asyncio.ensure_future(
            execute_shell_cmd(
                cmd=f"python {youwol.__path__[0]}/app/main.py --conf={config_path}",
                context=no_log_context,
            )
        )
        try:
            await wait_py_youwol_ready(port=port, context=ctx)
            yield PyYouwolSession(configuration=config)
        finally:
            stop_py_youwol(port=port)


class TestFailureResult(NamedTuple):
    name: List[str]
    py_youwol_logs: Optional[Awaitable[List[Log]]]
    output_summary: List[str]


class TestCounter(NamedTuple):
    OK: int = 0
    KO: int = 0

    def with_ok(self):
        return TestCounter(OK=self.OK + 1, KO=self.KO)

    def with_ko(self):
        return TestCounter(OK=self.OK, KO=self.KO + 1)

    def __str__(self):
        return f"Current status: {Fore.GREEN}{self.OK} OK, {Fore.RED}{self.KO} KO{Style.RESET_ALL}"


RunId = str
File = str
Test = str
PyYwLogsGetter = Callable[[PyYouwolSession, File, Test], Awaitable[List[Log]]]


class TestSession:
    result_folder: Path
    session_id: str
    asset_id: Optional[str] = None
    counter = TestCounter()

    def __init__(self, result_folder: Path, raw_id: str = None):
        self.result_folder = result_folder
        self.result_folder.mkdir()
        self.summary_path = self.result_folder / "summary.json"
        self.summary_path.write_text('{"results":[]}')
        self.session_id = str(datetime.now())
        self.raw_id = raw_id

    async def create_asset(self, context: Context):
        async with context.start("TestSession.create_asset") as ctx:  # type: Context
            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            body = {
                "rawId": self.session_id if not self.raw_id else self.raw_id,
                "kind": "py-youwol-consistency-testing",
                "name": f"Consistency_{self.session_id}.tests",
                "description": "Logs of IT executed with py-youwol",
                "tags": ["py-youwol", "test", "logs"],
            }
            await ctx.info(text="Create asset", data=body)
            gtw = LocalClients.get_assets_gateway_client(env=env)

            default_drive = (
                await gtw.get_treedb_backend_router().get_default_user_drive(
                    headers=ctx.headers()
                )
            )
            asset_resp = await gtw.get_assets_backend_router().create_asset(
                body=body,
                params=[("folder-id", default_drive["homeFolderId"])],
                headers=ctx.headers(),
            )
            self.asset_id = asset_resp["assetId"]
            await ctx.info(text="Asset created successfully", data=asset_resp)

    async def execute(
        self,
        py_yw_session: PyYouwolSession,
        title: str,
        action: Callable[[Context], Awaitable[Tuple[int, List[str]]]],
        errors_formatter: Callable[
            [PyYouwolSession, List[str], PyYwLogsGetter],
            Awaitable[List[TestFailureResult]],
        ],
        py_yw_logs_getter: PyYwLogsGetter,
        context: Context,
    ):
        if not self.asset_id:
            await self.create_asset(context=context)

        async with context.start("TestSession.execute") as ctx:  # type: Context
            run_id = str(datetime.now())
            start = time.time()
            await ctx.info(f"Run started @{start}")
            return_code, outputs = await action(ctx)
            end = time.time()
            await ctx.info(f"Run ended @{end}")

            data = parse_json(self.summary_path)
            await ctx.info("Run summary", data=data)
            to_publish = []
            if return_code != 0:
                print(f"{Fore.RED}ERROR while executing test{Style.RESET_ALL}")

                errors = await errors_formatter(
                    py_yw_session, outputs, py_yw_logs_getter
                )

                def to_logs_path():
                    return self.result_folder / f"logs_{uuid.uuid4()}.json"

                errors_output_file = [to_logs_path() for _ in errors]
                for error, path in zip(errors, errors_output_file):
                    logs = await error.py_youwol_logs
                    write_json(data={"nodes": [log.dict() for log in logs]}, path=path)
                    to_publish.append(path.name)

                filename = f"full_outputs{run_id}.txt"
                to_publish.append(filename)
                data["results"].append(
                    {
                        "runId": run_id,
                        "title": title,
                        "status": "KO",
                        "executionDate": run_id,
                        "duration": end - start,
                        "fullOutput": filename,
                        "errors": [
                            {
                                "name": error.name,
                                "outputSummary": error.output_summary,
                                "logsFile": str(path.relative_to(self.result_folder)),
                            }
                            for error, path in zip(errors, errors_output_file)
                        ],
                    }
                )

                Path(self.result_folder / filename).write_text(
                    "".join(outputs), encoding="UTF-8"
                )
                print(f"Error writen in {filename}")
                self.counter = self.counter.with_ko()
            else:
                data["results"].append(
                    {
                        "title": title,
                        "status": "OK",
                        "executionDate": run_id,
                        "duration": end - start,
                    }
                )
                print(f"{Fore.GREEN}SUCCESS while executing test{Style.RESET_ALL}")
                self.counter = self.counter.with_ok()

            print(self.counter)
            write_json(data, self.summary_path)
            to_publish.append(self.summary_path.name)
            try:
                await publish_files(
                    result_folder=self.result_folder,
                    files=to_publish,
                    asset_id=self.asset_id,
                    context=ctx,
                )
            except HTTPException:
                print(f"{Fore.RED}FAILED TO PUBLISH FILES{Style.RESET_ALL}")
            return return_code, outputs


async def publish_files(
    result_folder: Path,
    files: List[str],
    asset_id: str,
    context: Context,
):
    async with context.start("publish_files") as ctx:  # type: Context
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        with tempfile.TemporaryDirectory() as tmp_folder:
            base_path = Path(tmp_folder)
            zipper = zipfile.ZipFile(base_path / "asset.zip", "w", zipfile.ZIP_DEFLATED)
            for file in files:
                shutil.copy(result_folder / file, base_path / file)
                zipper.write(base_path / file, arcname=file)

            zipper.close()
            data = (Path(tmp_folder) / "asset.zip").read_bytes()

        gtw = LocalClients.get_assets_gateway_client(env=env)
        tokens = await get_connected_local_tokens(context=context)
        auth_token = await tokens.access_token()

        upload_resp = await gtw.get_assets_backend_router().add_zip_files(
            asset_id=asset_id,
            data=data,
            headers={**ctx.headers(), "authorization": f"Bearer {auth_token}"},
        )
        await ctx.info(text="Files uploaded successfully", data=upload_resp)
