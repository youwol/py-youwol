from starlette.requests import Request

from youwol_utils import log_info, get_user_id
from youwol_cdn_sessions_storage.configurations import Configuration


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = config.admin_headers if config.admin_headers else {}

    log_info("Successfully retrieved authorization for resources creation")
    await config.storage.ensure_bucket(headers=headers)
    log_info("resources initialization done")


def get_path(request: Request, package: str, name: str, namespace: str = None):
    user_id = get_user_id(request)
    full_package_name = package if not namespace else f"{namespace}/{package}"
    return f"{user_id}/{full_package_name}/{name}.json"
