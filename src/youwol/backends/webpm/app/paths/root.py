# third parties
from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse, StreamingResponse

# relative
from ..dependencies import Dependencies, dependenciesFactory
from ..metrics import count_root_redirection
from .common import client_response_to_streaming_response

router = APIRouter(tags=["webpm"])


@router.post("/loading-graph")
async def loading_graph(
    request: Request, deps: Dependencies = Depends(dependenciesFactory)
) -> StreamingResponse:
    token = await deps.session_less_token_manager.get_access_token()
    return await client_response_to_streaming_response(
        await deps.client_session.post(
            f"{deps.configuration.assets_gateway_base_url}/cdn-backend/queries/loading-graph",
            json=await request.json(),
            headers={"Authorization": f"Bearer {token}"},
        ),
    )


@router.get("/resource/{rest_of_path:path}")
async def resource(
    rest_of_path: str,
    deps: Dependencies = Depends(dependenciesFactory),
) -> StreamingResponse:
    token = await deps.session_less_token_manager.get_access_token()

    return await client_response_to_streaming_response(
        await deps.client_session.get(
            f"{deps.configuration.assets_gateway_base_url}/raw/package/{rest_of_path}",
            headers={"Authorization": f"Bearer {token}"},
        ),
    )


@router.get("/")
async def root_redirection(
    deps: Dependencies = Depends(dependenciesFactory),
) -> RedirectResponse:
    count_root_redirection.inc()
    return RedirectResponse(url=deps.configuration.root_redirection, status_code=301)
