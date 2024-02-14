# standard library
import json
import uuid

# third parties
from fastapi import APIRouter, Depends
from starlette.requests import Request

# Youwol backends
from youwol.backends.tree_db.configurations import Configuration, get_configuration

# Youwol utilities
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import (
    BorrowBody,
    ChildrenResponse,
    ItemBody,
    ItemResponse,
    ItemsResponse,
    PathResponse,
    RenameBody,
)

# relative
from ..utils import (
    db_delete,
    db_get,
    db_post,
    db_query,
    doc_to_item,
    get_folders_rec,
    get_parent,
    list_deleted,
)

router = APIRouter(tags=["treedb-backend.items"])


async def _create_item(
    folder_id: str, item: ItemBody, configuration: Configuration, context: Context
):
    async with context.start(action="_create_item") as ctx:
        items_db = configuration.doc_dbs.items_db
        parent = await get_parent(
            parent_id=folder_id, configuration=configuration, context=ctx
        )

        doc = {
            "item_id": item.itemId or str(uuid.uuid4()),
            "folder_id": folder_id,
            "related_id": item.assetId,
            "name": item.name,
            "type": item.kind,
            "group_id": parent["group_id"],
            "drive_id": parent["drive_id"],
            "metadata": json.dumps({"borrowed": item.borrowed}),
        }
        await db_post(docdb=items_db, doc=doc, context=ctx)

        response = doc_to_item(doc)
        return response


@router.put(
    "/folders/{folder_id}/items",
    summary="Create a new item.",
    response_model=ItemResponse,
)
async def create_item(
    request: Request,
    folder_id: str,
    item: ItemBody,
    configuration: Configuration = Depends(get_configuration),
) -> ItemResponse:
    """
    Creates a new item.

    Note:
        An item is related to an asset: before creating one, the corresponding asset should have been created
            (and its ID provided in the `item` parameter).

    Parameters:
        request: Incoming request.
        folder_id: ID of the parent folder.
        item: item properties.
        configuration: Injected configuration of the service.

    Return:
        Description of the folder.
    """
    async with Context.start_ep(
        request=request,
        action="create_item",
        body=item,
        with_attributes={"folder_id": folder_id},
    ) as ctx:  # type: Context
        return await _create_item(
            folder_id=folder_id, item=item, configuration=configuration, context=ctx
        )


@router.post(
    "/items/{item_id}",
    summary="Updates an item properties.",
    response_model=ItemResponse,
)
async def update_item(
    request: Request,
    item_id: str,
    body: RenameBody,
    configuration: Configuration = Depends(get_configuration),
) -> ItemResponse:
    """
    Updates an item properties.

    Parameters:
        request: Incoming request.
        item_id: ID of the item.
        body: Update details.
        configuration: Injected configuration of the service.

    Return:
        Description of the item.
    """
    async with Context.start_ep(
        request=request,
        action="update_item",
        body=body,
        with_attributes={"item_id": item_id},
    ) as ctx:  # type: Context
        items_db = configuration.doc_dbs.items_db
        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )
        doc = {**doc, **{"name": body.name}}
        await db_post(docdb=items_db, doc=doc, context=ctx)

        response = doc_to_item(doc)
        return response


async def _get_item(item_id: str, configuration: Configuration, context: Context):
    async with context.start(action="_get_item") as ctx:  # type: Context
        items_db = configuration.doc_dbs.items_db
        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )
        return doc_to_item(doc)


@router.get(
    "/items/{item_id}",
    summary="Retrieves properties of an item",
    response_model=ItemResponse,
)
async def get_item(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> ItemResponse:
    """
    Retrieves properties of an item.

    Parameters:
        request: Incoming request.
        item_id: ID of the item.
        configuration: Injected configuration of the service.

    Return:
        Description of the item.
    """
    async with Context.start_ep(
        request=request,
        action="get_item",
        with_attributes={"item_id": item_id},
    ) as ctx:  # type: Context
        response = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )
        return response


@router.get(
    "/items/from-asset/{asset_id}", summary="get an item", response_model=ItemsResponse
)
async def get_items_by_asset_id(
    request: Request,
    asset_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> ItemsResponse:
    """
    Retrieves the list of items associated to a corresponding `assetID`.
    From this list, one is the original item (not borrowed), the others are symbolic links (borrowed).

    Parameters:
        request: Incoming request.
        asset_id: ID of the corresponding asset.
        configuration: Injected configuration of the service.

    Return:
        Description of the item.
    """
    async with Context.start_ep(
        request=request,
        action="get_item",
        with_attributes={"assetId": asset_id},
    ) as ctx:  # type: Context
        docdb = configuration.doc_dbs.items_db
        items = await db_query(
            docdb=docdb, key="related_id", value=asset_id, max_count=100, context=ctx
        )

        response = ItemsResponse(items=[doc_to_item(item) for item in items])
        return response


@router.get(
    "/items/{item_id}/path",
    summary="get the path of an item",
    response_model=PathResponse,
)
async def get_path(
    request: Request,
    item_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> PathResponse:
    """
    Retrieves the full path of an item.

    Parameters:
        request: Incoming request.
        item_id: ID of the item.
        configuration: Injected configuration of the service.

    Return:
        Description of the path.
    """
    async with Context.start_ep(
        request=request,
        action="get_path",
        with_attributes={"item_id": item_id},
    ) as ctx:  # type: Context
        item = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )
        folders, drive = await get_folders_rec(
            folder_id=item.folderId,
            drive_id=item.driveId,
            configuration=configuration,
            context=ctx,
        )

        response = PathResponse(item=item, folders=folders, drive=drive)
        return response


@router.post(
    "/items/{item_id}/borrow", response_model=ItemResponse, summary="borrow item"
)
async def borrow(
    request: Request,
    item_id: str,
    body: BorrowBody,
    configuration: Configuration = Depends(get_configuration),
) -> ItemResponse:
    """
    Create a symbolic link of an item.

    Parameters:
        request: Incoming request.
        item_id: Item's ID.
        body: Borrow specification
        configuration: Injected configuration of the service.

    Return:
        Description of the resulting item.
    """
    async with Context.start_ep(
        request=request,
        action="borrow item",
        body=body,
        with_attributes={"item_id": item_id},
    ) as ctx:
        item = await _get_item(
            item_id=item_id, configuration=configuration, context=ctx
        )

        metadata = json.loads(item.metadata)
        metadata["borrowed"] = True
        item.itemId = body.targetId if body.targetId else str(uuid.uuid4())
        item.borrowed = True
        item.metadata = json.dumps(metadata)
        return await _create_item(
            folder_id=body.destinationFolderId,
            item=ItemBody(**item.dict()),
            configuration=configuration,
            context=ctx,
        )


@router.get(
    "/drives/{drive_id}/deleted",
    summary="list items of the drive queued for deletion",
    response_model=ChildrenResponse,
)
async def list_items_deleted(
    request: Request,
    drive_id: str,
    configuration: Configuration = Depends(get_configuration),
) -> ChildrenResponse:
    """
    Query the entities queued for deletion (moved into the 'trash').

    Parameters:
        request: Incoming request
        drive_id: parent drive's ID of the 'trash'.
        configuration: Injected configuration of the service.

    Return:
        Description of the children.
    """
    async with Context.start_ep(
        request=request, action="list_deleted"
    ) as ctx:  # type: Context
        response = await list_deleted(
            drive_id=drive_id, configuration=configuration, context=ctx
        )
        return response


@router.delete(
    "/items/{item_id}",
    summary="Queues an entity for deletion (moves into the 'trash').",
)
async def queue_delete_item(
    request: Request,
    item_id: str,
    erase: bool = False,
    configuration: Configuration = Depends(get_configuration),
):
    """
    Queues an item for deletion (moves into the 'trash').

    Parameters:
        request: Incoming request
        item_id: Item's ID.
        erase: if `True`, the entity is deleted directly (and not queued for deletion).
        configuration: Injected configuration of the service.

    Return:
        Empty JSON response.
    """
    async with Context.start_ep(
        request=request, action="queue_delete_item", with_attributes={"itemId": item_id}
    ) as ctx:  # type: Context
        dbs = configuration.doc_dbs
        items_db, _, _, deleted_db = (
            dbs.items_db,
            dbs.folders_db,
            dbs.drives_db,
            dbs.deleted_db,
        )

        doc = await db_get(
            partition_keys={"item_id": item_id}, docdb=items_db, context=ctx
        )

        if not erase:
            deleted_doc = {
                "deleted_id": doc["item_id"],
                "drive_id": doc["drive_id"],
                "type": doc["type"],
                "kind": "item",
                "related_id": doc["related_id"],
                "name": doc["name"],
                "parent_folder_id": doc["folder_id"],
                "group_id": doc["group_id"],
                "metadata": doc["metadata"],
            }
            deleted_db = configuration.doc_dbs.deleted_db
            await db_post(doc=deleted_doc, docdb=deleted_db, context=ctx)

        await db_delete(
            docdb=items_db,
            doc={"item_id": doc["item_id"], "group_id": doc["group_id"]},
            context=ctx,
        )
        return {}
