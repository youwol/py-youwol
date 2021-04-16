from pathlib import Path

from aiohttp import ClientConnectorError
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import FileResponse

from youwol.configuration.youwol_configuration import YouwolConfiguration, yw_config
from youwol.context import Context
from youwol.routers.frontends.utils import get_all_fronts
from youwol.web_socket import WebSocketsCache
from youwol_utils import aiohttp

import youwol.services.fronts.flux_builder as youwol_flux_builder
import youwol.services.fronts.flux_runner as youwol_flux_runner
import youwol.services.fronts.workspace_explorer as youwol_workspace_explorer
import youwol.services.fronts.dashboard_developer as youwol_dashboard_developer

router = APIRouter()


@router.get("/{service_name}/{rest_of_path:path}")
async def redirect_get_ui(
        request: Request,
        service_name: str,
        rest_of_path: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(
        web_socket=WebSocketsCache.ui_gateway,
        config=config,
        request=request
        )
    try:
        # Try to find a target with matching name in the config
        frontends = await get_all_fronts(context)
        frontend = next(frontend for frontend in frontends if frontend.info.name == service_name)
        url = f"http://localhost:{frontend.info.port}/{rest_of_path}"
        try:
            # Try to connect to a dev server
            async with aiohttp.ClientSession(auto_decompress=False) as session:
                async with await session.get(url=url) as resp:
                    content = await resp.read()
                    return Response(content=content, headers={k: v for k, v in resp.headers.items()})
        except ClientConnectorError:
            # Use the dist files
            rest_of_path = rest_of_path or 'index.html'
            path_dist = frontend.pipeline.build.dist
            path = Path(frontend.target.folder) / path_dist / rest_of_path
            return FileResponse(str(path))
    except (StopIteration, AttributeError):
        # No Target with matching name exist => if 'flux-builder', 'flux-runner', or 'assets-browser-ui'
        # => use dist files
        if service_name not in ['flux-builder', 'flux-runner', 'workspace-explorer', 'dashboard-developer',
                                'code-editor-ui']:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not known.")
        mappings = {
            'flux-builder': youwol_flux_builder,
            'flux-runner': youwol_flux_runner,
            'workspace-explorer': youwol_workspace_explorer,
            'dashboard-developer': youwol_dashboard_developer
            }
        rest_of_path = rest_of_path or 'index.html'
        path = Path(mappings[service_name].__file__).parent / rest_of_path
        return FileResponse(str(path))
