import asyncio
from pathlib import Path
from typing import List, Set, Tuple, cast

from dataclasses import dataclass
from fastapi import APIRouter, WebSocket, Depends
from starlette.requests import Request
from watchgod import awatch, Change

from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config, YouwolConfigurationFactory
from youwol.context import Context, ActionStep, Action
from youwol.routers.commons import SkeletonsResponse, SkeletonResponse, PostSkeletonBody
from youwol.routers.packages.synchronize import synchronize
from youwol.web_socket import WebSocketsCache

from youwol.routers.packages.models import (
    Package, StatusResponse, AllStatusResponse, TargetStatus,
    DependenciesResponse, ActionModule, AutoWatchBody
    )
from youwol.routers.packages.utils import (
    get_packages_status, get_all_packages,
    extract_below_dependencies_recursive, extract_above_dependencies_recursive, select_packages,
    )

from youwol.services.backs.cdn.utils import to_package_name
from youwol.routers.environment.router import status as env_status
router = APIRouter()


@dataclass(frozen=False)
class WatchMgr:

    web_socket: WebSocket
    tasks = {}

    @staticmethod
    def update(targets: List[Package], config: YouwolConfiguration):

        targets_dict = {t.info.name: t for t in targets}
        to_cancel = []
        for k, v in WatchMgr.tasks.items():
            if k not in targets_dict:
                to_cancel.append([k, v])

        for k, v in to_cancel:
            v.cancel()
            del WatchMgr.tasks[k]

        for k, v in targets_dict.items():
            if k not in WatchMgr.tasks:
                WatchMgr.tasks[k] = asyncio.run_coroutine_threadsafe(
                    watch_target(package=v, context=Context(config=config, web_socket=WatchMgr.web_socket)),
                    asyncio.get_event_loop()
                    )


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    await ws.accept()
    WebSocketsCache.modules = ws
    WatchMgr.web_socket = ws
    await ws.send_json({})
    while True:
        _ = await ws.receive_text()


@router.get("/status",
            summary="modules status",
            response_model=AllStatusResponse
            )
async def status(config: YouwolConfiguration = Depends(yw_config)):

    ws = WebSocketsCache.modules
    context = Context(config=config, web_socket=WebSocketsCache.modules)
    await ws.send_json({})
    all_status = await get_packages_status(context)

    def to_status_resp(d: TargetStatus):
        def doc():
            if not d.target.pipeline.documentation:
                return None
            link = d.target.pipeline.documentation(d.target)
            if isinstance(link, Path):
                return 'file://'+str(d.target.target.folder / link)
            return link

        resp = StatusResponse(assetId=d.target.assetId,
                              name=d.target.info.name,
                              category="",
                              version=d.target.info.version,
                              documentation=doc(),
                              installStatus=d.install_status.name if d.install_status else "",
                              buildStatus=d.build_status.name if d.build_status else "",
                              testStatus=d.test_status.name if d.test_status else "",
                              cdnStatus=d.cdn_status.name if d.cdn_status else "")
        return resp

    return AllStatusResponse(status=[to_status_resp(d) for d in all_status])


@router.post("/action",
             summary="execute action")
async def action(body: ActionModule, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, web_socket=WebSocketsCache.modules)

    build_targets, test_targets, cdn_targets, all_targets = \
        await select_packages(package_name=body.targetName,
                              action=body.action,
                              scope=body.scope,
                              context=context)

    coroutine = synchronize(build_targets=build_targets, test_targets=test_targets,
                            cdn_targets=cdn_targets, all_targets=all_targets, context=context)

    asyncio.run_coroutine_threadsafe(coroutine, asyncio.get_event_loop())
    return {}


@router.post("/{target_id}/install",
             summary="execute action")
async def install(
        request: Request,
        target_id: str,
        config: YouwolConfiguration = Depends(yw_config)):

    target_name = to_package_name(to_package_name(target_id))

    context = Context(config=config, web_socket=WebSocketsCache.modules).with_target(target_name)

    async with context.start(Action.INSTALL) as ctx:
        packages = await get_all_packages(ctx)
        package = next(p for p in packages if p.info.name == target_name)
        await package.pipeline.install.exe(resource=package, context=ctx)

    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(request, new_conf)


@router.get("/{target_id}/dependencies",
            response_model=DependenciesResponse,
            summary="execute action")
async def dependencies(target_id: str, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, web_socket=WebSocketsCache.modules)
    packages = await get_all_packages(context)
    target_name = to_package_name(to_package_name(target_id))
    below_dependencies = extract_below_dependencies_recursive(packages=packages, target_name=target_name)
    above_dependencies = extract_above_dependencies_recursive(packages=packages, target_name=target_name)

    return DependenciesResponse(belowDependencies=below_dependencies, aboveDependencies=list(above_dependencies))


@router.post("/watch", summary="set libraries to automatic 'watch'")
async def watch(body: AutoWatchBody, config: YouwolConfiguration = Depends(yw_config)):

    context = Context(config=config, web_socket=WebSocketsCache.modules)
    all_targets = await get_all_packages(context)
    watch_targets = [t for t in all_targets if t.info.name in body.libraries]
    WatchMgr.update(watch_targets, config)

    return {}


@router.get("/skeletons",
            response_model=SkeletonsResponse,
            summary="list the available skeletons")
async def skeletons(
        config: YouwolConfiguration = Depends(yw_config)
        ):
    resp_skeletons = [SkeletonResponse(name=name, description=p.skeleton.description, parameters=p.skeleton.parameters)
                      for name, p in config.userConfig.packages.pipelines.items() if p.skeleton]

    return SkeletonsResponse(skeletons=resp_skeletons)


@router.post("/skeletons/{pipeline}",
             summary="create skeleton")
async def create_skeletons(
        request: Request,
        pipeline: str,
        body: PostSkeletonBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    ctx = Context(config=config, web_socket=WebSocketsCache.modules)
    pipeline = config.userConfig.packages.pipelines[pipeline]
    skeleton = pipeline.skeleton
    await skeleton.generate(pipeline.skeleton.folder, body.parameters, pipeline, ctx)
    await YouwolConfigurationFactory.reload()
    new_conf = await yw_config()
    await env_status(request, new_conf)
    return {}


TypeChange = Set[Tuple[Change, str]]


async def watch_target(package: Package, context: Context):

    # async def handle_dist_change():
    #     ctx = context.with_target(package.info.name)
    #
    #     await ctx.with_action(Action.WATCH).info(
    #         ActionStep.STATUS,
    #         f"Watched changed on dist folder of package '{package.info.name}' \n")
    #
    #     packages = await get_all_packages(context)
    #     target = next(p for p in packages if p.info.name == package.info.name)
    #
    #     try:
    #         await make_package(package=target, context=ctx.with_action(Action.WATCH))
    #     except FileNotFoundError:
    #         print("Can not make package: a file is missing, likely build step not finished")
    #     except Exception as e:
    #         print("Can not make package, likely build step not finished")
    #         logging.exception(e)
    #         return
    #
    #     async with ctx.start(Action.CDN) as ctx:
    #         await publish_local_cdn(target, context=ctx)
    #
    #     await status(ctx.config)

    async def handle_src_change():
        ctx = context.with_target(package.info.name).with_action(Action.WATCH)
        await ctx.info(
            ActionStep.STATUS,
            f"Watched changed on src folder of package '{package.info.name}' \n"
            )
        await status(ctx.config)

    folder = package.target.folder
    coroutine = awatch(str(folder))

    async for changes in coroutine:
        print("handle changes")
        # not sure why the cast is needed (expecting Coroutine[Any,Any,TypeChange])
        src_path = folder / 'src'
        src_change = any([str(src_path) in c[1] for c in cast(TypeChange, changes)])
        src_change and await handle_src_change()
        # dist_path = folder / package.pipeline.build.dist
        # this is not right: we need to use target.category.build.checkSum
        # dist_change = any([str(dist_path) in c[1] for c in cast(TypeChange, changes)])
        # dist_change and await handle_dist_change()
