from context import Context
from routers.local_cdn.models import PackagesStatus, PackageDetails
from routers.upload.models import Library, PackageStatus
from utils_low_level import to_json


async def send_status(cdn_status: PackagesStatus, context: Context):
    message = {
        "target": 'PackagesStatus',
        "cdnStatus": to_json(cdn_status)
        }

    await context.web_socket.send_json(message)


async def send_details(package_details: PackageDetails, context: Context):
    message = {
        "target": 'PackageDetails',
        "packageDetails": to_json(package_details)
        }

    await context.web_socket.send_json(message)
