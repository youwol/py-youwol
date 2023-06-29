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
    AuthorizationProvider,
    Configuration,
    RemoteClients,
    configuration_from_python,
    default_auth_provider,
)
from youwol.app.routers.system.router import Log

# Youwol utilities
from youwol.utils import Context, OidcConfig, execute_shell_cmd, parse_json, write_json

colorama_init()


no_log_context = Context(logs_reporters=[], data_reporters=[])


async def wait_py_youwol_ready(port: int):
    async def handler(websocket):
        await websocket.recv()

    while True:
        try:
            async with ws_connect(f"ws://localhost:{port}/ws-data") as ws:
                await handler(ws)
            break
        except (ConnectionResetError, ConnectionRefusedError, InvalidMessage):
            pass


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
    config_path: Union[Path, str]
) -> AsyncContextManager[PyYouwolSession]:
    config = await configuration_from_python(Path(config_path))
    port = config.system.httpPort

    asyncio.ensure_future(
        execute_shell_cmd(
            cmd=f"python {youwol.__path__[0]}/main.py --conf={config_path}",
            context=no_log_context,
        )
    )
    try:
        await wait_py_youwol_ready(port=port)
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


class Publication(NamedTuple):
    remote_host: str
    client_id: str
    client_secret: str


class TestSession:
    result_folder: Path
    session_id: str
    publication: Publication
    asset_id: Optional[str] = None
    counter = TestCounter()

    def __init__(self, result_folder: Path, publication: Publication):
        self.result_folder = result_folder
        self.result_folder.mkdir()
        self.summary_path = self.result_folder / "summary.json"
        self.summary_path.write_text('{"results":[]}')
        self.session_id = str(datetime.now())
        self.publication = publication

    async def create_asset(self):
        gtw = await RemoteClients.get_assets_gateway_client(
            remote_host=self.publication.remote_host
        )
        headers = await get_headers(self.publication)
        default_drive = await gtw.get_treedb_backend_router().get_default_user_drive(
            headers=headers
        )
        asset_resp = await gtw.get_assets_backend_router().create_asset(
            body={
                "rawId": self.session_id,
                "kind": "py-youwol-consistency-testing",
                "name": f"Consistency_{self.session_id}.tests",
                "description": "Logs of IT executed with py-youwol",
                "tags": ["py-youwol", "test", "logs"],
            },
            params=[("folder-id", default_drive["homeFolderId"])],
            headers=headers,
        )
        self.asset_id = asset_resp["assetId"]
        print("Asset created successfully", asset_resp)

    async def execute(
        self,
        py_yw_session: PyYouwolSession,
        title: str,
        action: Callable[[], Awaitable[Tuple[int, List[str]]]],
        errors_formatter: Callable[
            [PyYouwolSession, List[str], PyYwLogsGetter],
            Awaitable[List[TestFailureResult]],
        ],
        py_yw_logs_getter: PyYwLogsGetter,
    ):
        if not self.asset_id:
            await self.create_asset()

        run_id = str(datetime.now())
        start = time.time()
        return_code, outputs = await action()
        end = time.time()
        data = parse_json(self.summary_path)
        to_publish = []
        if return_code != 0:
            print(f"{Fore.RED}ERROR while executing test{Style.RESET_ALL}")

            errors = await errors_formatter(py_yw_session, outputs, py_yw_logs_getter)

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
                publication=self.publication,
            )
        except HTTPException:
            print(f"{Fore.RED}FAILED TO PUBLISH FILES{Style.RESET_ALL}")
        return return_code, outputs


async def get_headers(publication: Publication):
    auth_provider = AuthorizationProvider(
        **default_auth_provider(platform_host=publication.remote_host)
    )
    token = (
        await OidcConfig(auth_provider.openidBaseUrl)
        .for_client(auth_provider.openidClient)
        .direct_flow(username=publication.client_id, password=publication.client_secret)
    )
    return {"authorization": f'Bearer {token["access_token"]}'}


async def publish_files(
    result_folder: Path, files: List[str], asset_id: str, publication: Publication
):
    with tempfile.TemporaryDirectory() as tmp_folder:
        base_path = Path(tmp_folder)
        zipper = zipfile.ZipFile(base_path / "asset.zip", "w", zipfile.ZIP_DEFLATED)
        for file in files:
            shutil.copy(result_folder / file, base_path / file)
            zipper.write(base_path / file, arcname=file)

        zipper.close()
        data = (Path(tmp_folder) / "asset.zip").read_bytes()

    gtw = await RemoteClients.get_assets_gateway_client(
        remote_host=publication.remote_host
    )
    headers = await get_headers(publication)

    upload_resp = await gtw.get_assets_backend_router().add_zip_files(
        asset_id=asset_id, data=data, headers=headers
    )
    print("Files uploaded", upload_resp)
