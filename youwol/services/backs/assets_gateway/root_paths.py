from fastapi import APIRouter, Depends
from starlette.requests import Request

from .configurations import get_configuration
from youwol_utils import (
    User, user_info, get_all_individual_groups, Group, private_group_id, to_group_id,
    GroupsResponse,
    )
from .routers import tree, assets, raw, cdn


router = APIRouter()

router.include_router(
    tree.router,
    prefix="/tree",
    dependencies=[Depends(get_configuration)],
    tags=["tree"]
    )

router.include_router(
    assets.router,
    prefix="/assets",
    dependencies=[Depends(get_configuration)],
    tags=["assets"]
    )

router.include_router(
    raw.router,
    prefix="/raw",
    dependencies=[Depends(get_configuration)],
    tags=["raw"]
    )

router.include_router(
    cdn.router,
    prefix="/cdn",
    dependencies=[Depends(get_configuration)],
    tags=["cdn"]
    )


@router.get("/.ambassador-internal/openapi-docs")
async def patch_until_this_call_is_removed():
    return {}


@router.get("/healthz")
async def healthz():
    return {"status": "assets-gateway ok"}


@router.get("/user-info",
            response_model=User,
            summary="retrieve user info"
            )
async def get_user_info(request: Request):

    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + \
             [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

    return User(name=user['preferred_username'], groups=groups)


@router.get("/groups",
            response_model=GroupsResponse,
            summary="list subscribed groups")
async def get_groups(request: Request):
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + [Group(id=str(to_group_id(g)), path=g)
                                                                   for g in groups if g]
    return GroupsResponse(groups=groups)
