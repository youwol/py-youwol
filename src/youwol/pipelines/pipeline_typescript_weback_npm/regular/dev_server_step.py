# standard library
import uuid

from asyncio.subprocess import Process
from pathlib import Path

# third parties
from aiohttp import ClientSession
from fastapi import HTTPException
from starlette.responses import Response

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.environment.proxied_esm_servers import EsmServerDispatchInput
from youwol.app.routers.environment.router import emit_environment_status
from youwol.app.routers.projects import (
    CommandPipelineStep,
    ExplicitNone,
    FlowId,
    PipelineStep,
    Project,
    get_project_configuration,
)

# Youwol utilities
from youwol.utils import (
    CdnClient,
    CommandException,
    Context,
    Label,
    encode_id,
    execute_shell_cmd,
    find_available_port,
)

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.regular.webpack_dev_server_switch import (
    dispatch_dev_server,
)


async def get_info(project: Project, context: Context):

    async with context.start("get_intput_data") as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        proxy = env.proxied_esm_servers.get(
            package=project.name,
            version=project.version,
        )
        if not proxy:
            raise HTTPException(
                status_code=404, detail="The dev. server is not listening"
            )
        return proxy.info()


async def stop_dev_server(project: Project, context: Context):

    async with context.start("stop_backend") as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        proxy = env.proxied_esm_servers.get(
            package=project.name,
            version=project.version,
        )
        if proxy:
            await env.proxied_esm_servers.terminate(uid=proxy.uid, context=ctx)
            await emit_environment_status(context=ctx)
            return {"status": "Dev. server terminated"}

        return {"status": "Dev. server proxy not found."}


class DevServerStep(PipelineStep):
    """
    Starts the service.
    """

    id: str = "dev-server"
    """
    ID of the step.

    Warning:
        The flows defined in this pipelines reference this ID, in common scenarios it should not be modified.
    """

    run: ExplicitNone = ExplicitNone()
    """
    Step execution is defined by the method `execute_run`.
    """
    view: str = Path(__file__).parent / "views" / "dev-server.view.js"
    """
    The view of the step allows to start/stop the underlying dev. server with different options.
    """
    http_commands: list[CommandPipelineStep] = [
        CommandPipelineStep(
            name="get_info",
            do_get=lambda project, flow_id, ctx: get_info(project=project, context=ctx),
        ),
        CommandPipelineStep(
            name="stop_dev_server",
            do_get=lambda project, flow_id, ctx: stop_dev_server(
                project=project, context=ctx
            ),
        ),
    ]
    """
    Commands associated to the step:
    *  `get_info` : return the info of associated backend.
    See :meth:`get_info <youwol.app.environment.proxied_backends.BackendsStore.get_info>`.
    *  `stop_backend` : stop the backend proxied from the associated project's name & version.
    """

    async def execute_run(self, project: Project, flow_id: FlowId, context: Context):
        """
        Start the dev. server & install the proxy.

        Parameters:
            project: Target project.
            flow_id: Target flow.
            context: Current context.
        """

        proxy_uid = str(uuid.uuid4())

        async with context.start(
            "run_command",
            with_labels=[Label.ESM_SERVER],
            with_attributes={
                "package": project.name,
                "version": project.version,
                "proxyUid": proxy_uid,
            },
        ) as ctx:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
            local_cdn: CdnClient = LocalClients.get_cdn_client(env=env)
            try:
                await local_cdn.get_version_info(
                    library_id=encode_id(project.name),
                    version=project.version,
                    headers=ctx.headers(),
                )
            except HTTPException as e:
                if e.status_code == 404:
                    raise CommandException(
                        command="start dev. server",
                        outputs=[
                            f"The package at version {project.version} is not available in the local CDN.",
                            "Please publish the package to the local CDN before starting the dev server.",
                            "You can publish the package by running the 'cdn-local' step.",
                        ],
                    ) from e
                raise e
            config = await get_project_configuration(
                project_id=project.id, flow_id=flow_id, step_id=self.id, context=ctx
            )
            config = {
                "installDispatch": True,
                "autoRun": True,
                "port": "auto",
                **config,
            }

            port = find_available_port(start=2010, end=3000)

            async def on_executed(process: Process | None, shell_ctx: Context):
                if config["installDispatch"]:
                    await env.proxied_esm_servers.register(
                        uid=proxy_uid,
                        package=project.name,
                        version=project.version,
                        port=port,
                        process=process,
                        dispatch=self.dispatch,
                        wait_timeout=5,
                    )
                    await emit_environment_status(context=shell_ctx)
                    await shell_ctx.info(
                        text=f"Dispatch requests targeting package '{project.name}#{project.version}' "
                        f"to dev. server running on 'localhost:{port}"
                    )
                if process:
                    await shell_ctx.info(
                        text=f"Dev server started (pid='{process.pid}') on {port}"
                    )

            if config["autoRun"]:
                shell_cmd = f"yarn start --port {port}"
                return_code, outputs = await execute_shell_cmd(
                    cmd=shell_cmd,
                    context=ctx,
                    log_outputs=True,
                    on_executed=on_executed,
                    cwd=project.path,
                )
                if return_code > 0:
                    raise CommandException(command=shell_cmd, outputs=outputs)
                return outputs

            await on_executed(process=None, shell_ctx=ctx)
            return [
                f"Proxy '{project.name}#{project.version}' => 'localhost:{port}' installed",
                f"Service not started, please serve it using 'yarn start --port {port}'",
            ]

    @staticmethod
    async def dispatch(dispatch_input: EsmServerDispatchInput, context: Context):

        headers = context.headers(from_req_fwd=lambda header_keys: header_keys)

        async def fwd_request(rest_of_path: str) -> Response | None:
            async with ClientSession(auto_decompress=False) as session:
                async with await session.get(
                    url=f"http://localhost:{dispatch_input.port}/{rest_of_path}",
                    headers=headers,
                ) as fwd_resp:
                    if fwd_resp.status < 400:
                        content = await fwd_resp.read()
                        return Response(
                            status_code=fwd_resp.status,
                            content=content,
                            headers=dict(fwd_resp.headers.items()),
                        )

        async with context.start("PipelineTS devServer dispatch") as ctx:
            return await dispatch_dev_server(
                package=dispatch_input.package,
                version=dispatch_input.version,
                request=dispatch_input.request,
                target=dispatch_input.target,
                fwd_request=fwd_request,
                context=ctx,
            )
