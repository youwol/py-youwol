# standard library
from enum import Enum

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.http_clients.cdn_backend import WebpmLibraryType

CDN_TOPIC = "cdn"


class CdnVersionLight(BaseModel):
    version: str
    type: WebpmLibraryType


class CdnVersion(CdnVersionLight):
    filesCount: int
    entryPointSize: int  # total size, in bytes


class CdnPackage(BaseModel):
    name: str
    id: str
    versions: list[CdnVersion]


class CdnPackageLight(BaseModel):
    name: str
    id: str
    versions: list[CdnVersionLight]


class CdnStatusResponse(BaseModel):
    packages: list[CdnPackageLight]


class CdnPackageResponse(CdnPackage):
    pass


class UpdateStatus(Enum):
    UP_TO_DATE = "upToDate"
    MISMATCH = "mismatch"
    REMOTE_AHEAD = "remoteAhead"
    LOCAL_AHEAD = "localAhead"


class PackageVersionInfo(BaseModel):
    version: str
    fingerprint: str


class CheckUpdateResponse(BaseModel):
    packageName: str
    localVersionInfo: PackageVersionInfo
    remoteVersionInfo: PackageVersionInfo
    status: UpdateStatus


class CheckUpdatesResponse(BaseModel):
    updates: list[CheckUpdateResponse]


class DownloadPackageBody(BaseModel):
    packageName: str
    version: str


class DownloadPackagesBody(BaseModel):
    packages: list[DownloadPackageBody]
    checkUpdateStatus: bool


class ResetCdnBody(BaseModel):
    keepProjectPackages: bool = True


class ResetCdnResponse(BaseModel):
    deletedPackages: list[str]


class HardResetDbStatus(BaseModel):
    remainingCount: int
    originalCount: int


class HardResetCdnResponse(BaseModel):
    cdnLibraries: HardResetDbStatus
    assetEntities: HardResetDbStatus
    assetAccess: HardResetDbStatus
    treedbItems: HardResetDbStatus
    treedbDeleted: HardResetDbStatus


class DownloadedPackageResponse(BaseModel):
    packageName: str
    version: str
    versions: list[str]
    fingerprint: str


class Event(Enum):
    DOWNLOAD_STARTED = "downloadStarted"
    DOWNLOAD_DONE = "downloadDone"
    UPDATE_CHECK_STARTED = "updateCheckStarted"
    UPDATE_CHECK_DONE = "updateCheckDone"


class PackageEventResponse(BaseModel):
    packageName: str
    version: str
    event: Event
