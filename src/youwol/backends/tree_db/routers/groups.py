# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import (
    Configuration,
    Constants,
    get_configuration,
)

# Youwol utilities
from youwol.utils import (
    ensure_group_permission,
    get_all_individual_groups,
    private_group_id,
    to_group_id,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    DefaultDriveResponse,
    DriveBody,
    DriveResponse,
    DrivesResponse,
    Group,
    GroupsResponse,
)

# relative
from ..utils import create_drive, doc_to_drive_response, get_default_drive

router = APIRouter(tags=["treedb-backend.groups"])


@router.get(
    "/groups", response_model=GroupsResponse, summary="List user's subscribed groups."
)
async def get_groups(request: Request) -> GroupsResponse:
    """
    Lists user's subscribed groups.

    Parameters:
        request: Incoming request.

    Return:
        User's groups.
    """
    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    return GroupsResponse(
        groups=(
            [Group(id=private_group_id(user), path="private")]
            + [Group(id=str(to_group_id(g)), path=g) for g in groups if g]
        )
    )


@router.put(
    "/groups/{group_id}/drives",
    summary="Create a new drive.",
    response_model=DriveResponse,
)
async def create_group_drive(
    request: Request,
    group_id: str,
    drive: DriveBody,
    configuration: Configuration = Depends(get_configuration),
) -> DriveResponse:
    """
    Creates a new drive.

    Parameters:
        request: Incoming request.
        group_id: Group in which the drive belongs.
        drive: Description of the drive.
        configuration: Injected configuration of the service.

    Return:
        Drive attributes.
    """

    async with Context.start_ep(
        request=request, action="create drive", body=drive
    ) as ctx:  # type: Context
        response = await create_drive(
            group_id=group_id, drive=drive, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/groups/{group_id}/drives",
    summary="List the available drives under a particular group.",
    response_model=DrivesResponse,
)
async def list_drives(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DrivesResponse:
    """
    Lists the available drives under a particular group.

    Parameters:
        request: Incoming request.
        group_id: Group in which the drives belong.
        configuration: Injected configuration of the service.

    Return:
        The list of available drives.
    """
    async with Context.start_ep(
        request=request,
        action="list_drives",
        with_attributes={"groupId": group_id},
    ) as ctx:  # type: Context
        ensure_group_permission(request=request, group_id=group_id)

        docdb_drive = configuration.doc_dbs.drives_db
        drives = await docdb_drive.query(
            query_body=f"group_id={group_id}#100",
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )
        response = DrivesResponse(
            drives=[doc_to_drive_response(d) for d in drives["documents"]]
        )
        return response


@router.get(
    "/groups/{group_id}/default-drive",
    response_model=DefaultDriveResponse,
    summary="Retrieves the default drive of a group.",
)
async def get_group_default_drive(
    request: Request,
    group_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> DefaultDriveResponse:
    """
    Retrieves properties of the default drive of a group.

    Parameters:
        request: Incoming request.
        group_id: ID of the parent group.
        configuration: Injected configuration of the service.

    Return:
        Description of the drive.
    """
    return await get_default_drive(request, group_id, configuration)
