from enum import Enum
from typing import List

from pydantic import BaseModel


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


class DownloadedPackageResponse(BaseModel):
    packageName: str
    version: str
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
