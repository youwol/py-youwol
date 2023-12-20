# typing
from typing import Optional

# third parties
from starlette.requests import Request

# Youwol utilities
from youwol.utils import get_user_id


def get_path(
    request: Request, package: str, name: str, namespace: Optional[str] = None
):
    user_id = get_user_id(request)
    full_package_name = package if not namespace else f"{namespace}/{package}"
    return f"{user_id}/{full_package_name}/{name}.json"
