# typing
from typing import Generic, TypeVar

# third parties
from pydantic import BaseModel

# Youwol clients
from yw_clients.http.assets import AssetResponse

RawT = TypeVar("RawT", bound=BaseModel)
"""
Generic specification of the type of a raw response when creating an asset.
"""


class NewAssetResponse(AssetResponse, Generic[RawT]):
    """
    Asset description when creating an asset using
    :func:`create_asset <youwol.backends.assets_gateway.routers.assets_backend.create_asset>`
    """

    itemId: str
    """
    Item ID
    """
    rawResponse: RawT
    """
    Response from the underlying service manager of the 'raw' part of the asset; if any.
    """
