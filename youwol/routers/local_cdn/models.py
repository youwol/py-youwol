from enum import Enum
from typing import List

from pydantic import BaseModel


class CdnVersion(BaseModel):
    version: str
    filesCount: int
    entryPointSize: int  # total size, in bytes


class CdnPackage(BaseModel):
    name: str
    id: str
    versions: List[CdnVersion]


class CdnStatusResponse(BaseModel):
    packages: List[CdnPackage]


class CdnPackageResponse(CdnPackage):
    pass


class UpdateStatus(Enum):
    upToDate = 'upToDate'
    mismatch = 'mismatch'
    remoteAhead = "remoteAhead"
    localAhead = "localAhead"


class PackageVersionInfo(BaseModel):
    version: str
    fingerprint: str


class CheckUpdateResponse(BaseModel):
    packageName: str
    localVersionInfo: PackageVersionInfo
    remoteVersionInfo: PackageVersionInfo
    status: UpdateStatus


class CheckUpdatesResponse(BaseModel):
    updates: List[CheckUpdateResponse]


class DownloadPackageBody(BaseModel):
    packageName: str
    version: str


class DownloadPackagesBody(BaseModel):
    packages: List[DownloadPackageBody]
    checkUpdateStatus: bool


class ResetCdnBody(BaseModel):
    keepProjectPackages: bool = True


class DownloadedPackageResponse(BaseModel):
    packageName: str
    version: str
    versions: List[str]
    fingerprint: str


class Event(Enum):
    downloadStarted = 'downloadStarted'
    downloadDone = 'downloadDone'
    updateCheckStarted = 'updateCheckStarted'
    updateCheckDone = 'updateCheckDone'


class PackageEvent(BaseModel):
    packageName: str
    version: str
    event: Event
