"""
This configuration is commonly used for integration testing of npm packages along with py-youwol environment.
It connects to the 'integration' environment of YouWol when needed.
You need to provide as environment variables: USERNAME_INTEGRATION_TESTS & PASSWORD_INTEGRATION_TESTS
"""

# standard library
import os
import shutil

from pathlib import Path

# third parties
import brotli

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import (
    CloudEnvironment,
    CloudEnvironments,
    Command,
    Configuration,
    Connection,
    CustomEndPoints,
    Customization,
    CustomMiddleware,
    DirectAuth,
    IConfigurationFactory,
    LocalEnvironment,
    System,
    TokensStorageInMemory,
    YouwolEnvironment,
    get_standard_auth_provider,
)
from youwol.app.main_args import MainArguments
from youwol.app.routers.projects import ProjectLoader

# Youwol utilities
from youwol.utils.context import Context, Label

user_name = os.getenv("USERNAME_INTEGRATION_TESTS")
cloud_env = CloudEnvironment(
    envId="integration",
    host="platform.int.youwol.com",
    authProvider=get_standard_auth_provider("platform.int.youwol.com"),
    authentications=[
        DirectAuth(
            authId=user_name,
            userName=user_name,
            password=os.getenv("PASSWORD_INTEGRATION_TESTS"),
        )
    ],
)


async def reset(ctx: Context):
    env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
    env.reset_cache()
    env.reset_databases()
    parent_folder = env.pathsBook.config.parent
    shutil.rmtree(parent_folder / "projects", ignore_errors=True)
    shutil.rmtree(parent_folder / "youwol_system", ignore_errors=True)
    os.mkdir(parent_folder / "projects")
    await ProjectLoader.initialize(env=env)


class BrotliDecompressMiddleware(CustomMiddleware):
    """
    This middleware is required because using jest and its jsDOM environment, automatic brotli decompression is
    not done.
    """

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


Configuration(
    system=System(
        httpPort=2001,
        tokensStorage=TokensStorageInMemory(),
        cloudEnvironments=CloudEnvironments(
            defaultConnection=Connection(envId="integration", authId=user_name),
            environments=[cloud_env],
        ),
        localEnvironment=LocalEnvironment(
            dataDir=Path(__file__).parent / "databases",
            cacheDir=Path(__file__).parent / "youwol_system",
        ),
    ),
    customization=Customization(
        middlewares=[
            BrotliDecompressMiddleware(),
        ],
        endPoints=CustomEndPoints(
            commands=[
                Command(name="reset", do_get=reset),
            ]
        ),
    ),
)
