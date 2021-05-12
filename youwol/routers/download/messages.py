from youwol.context import Context
from youwol.routers.upload.models import PackageStatus


async def send_version_pending(raw_id: str, name: str,  version: str, context: Context):
    message = {
        "target": 'downloadItem',
        "name": name,
        "raw_id": raw_id,
        "version": version,
        "status": str(PackageStatus.PROCESSING)
        }
    await context.web_socket.send_json(message)


async def send_version_resolved(raw_id: str, name: str, version: str, status: PackageStatus,  context: Context):
    message = {
        "target": 'downloadItem',
        "name": name,
        "rawId": raw_id,
        "version": version,
        "status": str(status)
        }
    await context.web_socket.send_json(message)
