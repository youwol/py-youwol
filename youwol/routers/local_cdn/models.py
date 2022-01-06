from typing import List

from pydantic import BaseModel


class PackageVersion(BaseModel):
    version: str
    versionNumber: int


class Package(BaseModel):
    name: str
    versions: List[PackageVersion]


class PackagesStatus(BaseModel):
    packages: List[Package]


class VersionDetails(BaseModel):
    name: str
    version: str
    versionNumber: int
    filesCount: int
    bundleSize: int
    path: List[str]
    namespace: str


class PackageDetails(BaseModel):
    name: str
    versions: List[VersionDetails]
