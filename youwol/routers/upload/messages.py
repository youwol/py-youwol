from youwol.context import Context
from youwol.routers.upload.models import Library, PackageStatus


async def send_package_pending(package: Library, context: Context):
    message = {
        "target": 'package',
        "assetId": package.assetId,
        "name": package.libraryName,
        "namespace": package.namespace,
        "treeItems": [item.dict() for item in package.treeItems],
        "releases": [r.dict() for r in package.releases],
        "status": str(PackageStatus.PROCESSING)
        }

    await context.web_socket.send_json(message)


async def send_package_resolved(package: Library, asset_status: PackageStatus, tree_status: PackageStatus,
                                cdn_status: PackageStatus, context: Context):
    message = {
        "target": 'package',
        "assetId": package.assetId,
        "name": package.libraryName,
        "namespace": package.namespace,
        "treeItems": [item.dict() for item in package.treeItems],
        "releases": [r.dict() for r in package.releases],
        "status": {
                'assetStatus': str(asset_status),
                'treeStatus': str(tree_status),
                'cdnStatus': str(cdn_status),
                }
        }
    await context.web_socket.send_json(message)


async def send_version_pending(asset_id: str, name: str,  version: str, context: Context):
    message = {
        "target": 'packageVersion',
        "assetId": asset_id,
        "name": name,
        "version": version,
        "status": str(PackageStatus.PROCESSING)
        }
    await context.web_socket.send_json(message)


async def send_version_resolved(asset_id: str, name: str, version: str, status: PackageStatus,  context: Context):
    message = {
        "target": 'packageVersion',
        "assetId": asset_id,
        "name": name,
        "version": version,
        "status": str(status)
        }
    await context.web_socket.send_json(message)
