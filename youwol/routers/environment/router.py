import asyncio
import itertools
from typing import List, Optional, Dict, cast

from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

from youwol.backends.treedb.models import PathResponse
from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.models import UserInfo
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment, YouwolEnvironmentFactory
from youwol.routers.commons import Label
from youwol.routers.commons import ensure_path
from youwol.routers.environment.models import (
    SyncUserBody, LoginBody, RemoteGatewayInfo, SelectRemoteBody, AvailableProfiles, ProjectsLoadingResults
)
from youwol.routers.environment.upload_assets.data import UploadDataTask
from youwol.routers.environment.upload_assets.flux_project import UploadFluxProjectTask
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol.routers.environment.upload_assets.package import UploadPackageTask
from youwol.routers.environment.upload_assets.story import UploadStoryTask
from youwol.routers.environment.upload_assets.upload import synchronize_permissions_metadata_symlinks
from youwol.utils.utils_low_level import get_public_user_auth_token
from youwol.web_socket import UserContextLogger
from youwol_utils import retrieve_user_info, decode_id
from youwol_utils.clients.assets.assets import AssetsClient
from youwol_utils.clients.treedb.treedb import TreeDbClient
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json, write_json

router = APIRouter()
flatten = itertools.chain.from_iterable


class EnvironmentStatusResponse(BaseModel):
    configuration: YouwolEnvironment
    users: List[str]
    userInfo: UserInfo
    remoteGatewayInfo: Optional[RemoteGatewayInfo]
    remotesInfo: List[RemoteGatewayInfo]


async def connect_to_remote(config: YouwolEnvironment, context: Context) -> bool:
    remote_gateway_info = config.get_remote_info()
    if not remote_gateway_info:
        return False

    try:
        await config.get_auth_token(context)
        client = await RemoteClients.get_assets_gateway_client(context)
        await client.healthz()
        return True
    except HTTPException as e:
        await context.info(
            text="Authorization: HTTP Error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ClientConnectorError as e:
        await context.info(
            text="Authorization: Connection error (internet on?)",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except RuntimeError as e:
        await context.info(
            text="Authorization error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ContentTypeError as e:
        await context.info(
            text="Failed to call healthz on assets-gateway",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False


@router.get("/configuration",
            response_model=YouwolEnvironment,
            summary="configuration")
async def configuration(
        config: YouwolEnvironment = Depends(yw_config)
):
    return config


@router.post("/configuration",
             response_model=EnvironmentStatusResponse,
             summary="reload configuration")
async def reload_configuration(
        request: Request,
):
    env = await YouwolEnvironmentFactory.reload()
    return await status(request, env)


@router.get("/configuration/profiles/",
            response_model=AvailableProfiles,
            summary="list available configuration profiles")
async def change_configuration_profile(
        config: YouwolEnvironment = Depends(yw_config)
):
    return AvailableProfiles(profiles=config.available_profiles,
                             active=config.active_profile)


@router.put("/configuration/profiles/active",
            response_model=EnvironmentStatusResponse,
            summary="change configuration profile")
async def change_configuration_profile(
        request: Request,
        body: AvailableProfiles,
        config: YouwolEnvironment = Depends(yw_config)
):
    profile = body.active
    if profile == config.active_profile:
        raise HTTPException(status_code=409, detail=f"current configuration profile is already '{profile}'")
    if profile not in config.available_profiles:
        raise HTTPException(status_code=404, detail=f"no configuration profile '{profile}'")

    env = await YouwolEnvironmentFactory.reload(profile)
    return await status(request, env)


@router.get("/file-content",
            summary="text content of the configuration file")
async def file_content(
        config: YouwolEnvironment = Depends(yw_config)
):
    return {
        "content": config.pathsBook.config.read_text()
    }


@router.get("/status",
            response_model=EnvironmentStatusResponse,
            summary="status")
async def status(
        request: Request,
        config: YouwolEnvironment = Depends(yw_config)
):

    async with Context.from_request(request).start(
            action="Get environment status",
            logger=UserContextLogger()
    ) as ctx:
        connected = await connect_to_remote(config=config, context=ctx)
        remote_gateway_info = config.get_remote_info()
        if remote_gateway_info:
            remote_gateway_info = RemoteGatewayInfo(name=remote_gateway_info.name,
                                                    host=remote_gateway_info.host,
                                                    connected=connected)
        remotes_info = parse_json(config.pathsBook.remotesInfo)['remotes'].values()
        response = EnvironmentStatusResponse(
            users=config.get_users_list(),
            userInfo=config.get_user_info(),
            configuration=config,
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=list(remotes_info)
        )
        await ctx.send(response)
        await ctx.send(ProjectsLoadingResults(results=await ProjectLoader.get_results(config, ctx)))
        return response


@router.post("/login",
             summary="log in as specified user")
async def login(
        request: Request,
        body: LoginBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    await YouwolEnvironmentFactory.login(email=body.email, remote_name=config.selectedRemote)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/select-remote-gateway",
             summary="select a remote")
async def select_remote(
        request: Request,
        body: SelectRemoteBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    await YouwolEnvironmentFactory.login(email=config.userEmail, remote_name=body.name)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/sync-user",
             summary="sync a new local user w/ remote one")
async def sync_user(
        request: Request,
        body: SyncUserBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.from_request(request).start(
            action=f"Sync. user {body.email}",
            logger=UserContextLogger()
            ) as ctx:

        try:
            auth_token = await get_public_user_auth_token(
                username=body.email,
                pwd=body.password,
                client_id=config.get_remote_info().metadata['keycloakClientId'],
                openid_host=config.openid_host
            )
        except Exception:
            raise RuntimeError(f"Can not authorize from email/pwd @ {config.get_remote_info().host}")

        await ctx.info(text="Login successful")

        secrets = parse_json(config.pathsBook.secrets)
        if body.email in secrets:
            secrets[body.email] = {**secrets[body.email], **{"password": body.password}}
        else:
            secrets[body.email] = {"password": body.password}
        write_json(secrets, config.pathsBook.secrets)

        user_info = await retrieve_user_info(auth_token=auth_token, openid_host=config.openid_host)

        users_info = parse_json(config.pathsBook.usersInfo)
        users_info['users'][body.email] = {
            "id": user_info['sub'],
            "name": user_info['preferred_username'],
            "memberOf": user_info['memberof'],
            "email": user_info["email"]
        }
        write_json(users_info, config.pathsBook.usersInfo)
        await login(request=request, body=LoginBody(email=body.email), config=config)
        return users_info['users'][body.email]


@router.post("/upload/{asset_id}",
             summary="upload an asset")
async def select_remote(
        request: Request,
        asset_id: str
):
    upload_factories: Dict[str, any] = {
        "data": UploadDataTask,
        "flux-project": UploadFluxProjectTask,
        "story": UploadStoryTask,
        "package": UploadPackageTask
    }

    async with Context.from_request(request).start(
            action="upload_asset",
            with_attributes={
                'asset_id': asset_id
            },
            logger=UserContextLogger()
    ) as ctx:

        env = await ctx.get('env', YouwolEnvironment)
        local_treedb: TreeDbClient = LocalClients.get_treedb_client(env=env)
        local_assets: AssetsClient = LocalClients.get_assets_client(env=env)
        raw_id = decode_id(asset_id)
        asset, tree_item = await asyncio.gather(
            local_assets.get(asset_id=asset_id),
            local_treedb.get_item(item_id=asset_id),
            return_exceptions=True
        )
        if isinstance(asset, HTTPException) and asset.status_code == 404:
            await ctx.error(text="Can not find the asset in the local assets store")
            raise RuntimeError("Can not find the asset in the local assets store")
        if isinstance(tree_item, HTTPException) and tree_item.status_code == 404:
            await ctx.error(text="Can not find the tree item in the local treedb store")
            raise RuntimeError("Can not find the tree item in the local treedb store")
        if isinstance(asset, Exception) or isinstance(tree_item, Exception):
            raise RuntimeError("A problem occurred while fetching the local asset/tree items")
        asset = cast(Dict, asset)
        tree_item = cast(Dict, tree_item)

        factory: UploadTask = upload_factories[asset['kind']](
            raw_id=raw_id,
            asset_id=asset_id,
            context=ctx
        )

        local_data = await factory.get_raw()
        try:
            path_item = await local_treedb.get_path(item_id=tree_item['itemId'])
        except HTTPException as e:
            if e.status_code == 404:
                await ctx.error(text=f"Can not get path of item with id '{tree_item['itemId']}'",
                                data={"tree_item": tree_item, "error_detail": e.detail})
            raise e

        await ctx.info(
            text="Data retrieved",
            data={"path_item": path_item, "raw data": local_data}
        )

        assets_gtw_client = await RemoteClients.get_assets_gateway_client(context=ctx)

        await ensure_path(path_item=PathResponse(**path_item), assets_gateway_client=assets_gtw_client)
        try:
            _asset = await assets_gtw_client.get_asset_metadata(asset_id=asset_id)
            _tree_item = await assets_gtw_client.get_tree_item(tree_item['itemId'])
            await ctx.info(
                text="Asset already found in deployed environment"
            )
            await factory.update_raw(data=local_data, folder_id=tree_item['folderId'])
        except HTTPException as e:
            if e.status_code != 404:
                raise e
            await ctx.info(
                labels=[Label.RUNNING],
                text="Project not already found => start creation"
            )
            await factory.create_raw(data=local_data, folder_id=tree_item['folderId'])

        await synchronize_permissions_metadata_symlinks(
            asset_id=asset_id,
            tree_id=tree_item['itemId'],
            assets_gtw_client=assets_gtw_client,
            context=ctx
        )

    return {}
