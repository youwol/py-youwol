from enum import Enum
from typing import NamedTuple, List, Union
from pydantic import BaseModel, Json

from youwol.configuration.models_package import TargetPackage, InfoPackage, PipelinePackage
from youwol.context import Action
from youwol.services.backs.cdn.utils import to_package_id

TargetId = str


class Package(BaseModel):
    assetId: str
    pipeline: PipelinePackage
    target: TargetPackage
    info: InfoPackage

    def cdn_base_path(self):
        asset_id = to_package_id(self.info.name)
        return f"/api/assets-gateway/raw/package/{asset_id}/{self.info.version}"


class StatusResponse(BaseModel):
    assetId: str
    name: str
    documentation: Union[str, None]
    category: str
    version: str
    installStatus: str
    buildStatus: str
    testStatus: str
    cdnStatus: str


class AllStatusResponse(BaseModel):
    status: List[StatusResponse]


class DependenciesResponse(BaseModel):
    aboveDependencies: List[str]
    belowDependencies: List[str]


class AutoWatchBody(BaseModel):
    libraries: List[str]


class MessageWebSocket(BaseModel):
    action: str
    level: str
    step: str
    target: str
    content: Union[Json, str]


class ActionScope(Enum):
    TARGET_ONLY = "TARGET_ONLY"
    ALL_ABOVE = "ALL_ABOVE"
    ALL_BELOW = "ALL_BELOW"
    ALL = "ALL"


class ActionModule(BaseModel):
    action: Action
    targetName: str
    scope: ActionScope


class InstallStatus(Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    INSTALLED = "INSTALLED"


class BuildStatus(Enum):
    NA = "NA"
    SYNC = "SYNC"
    RED = "RED"
    NEVER_BUILT = "NEVER_BUILT"
    OUT_OF_DATE = "OUT_OF_DATE"
    INDIRECT_OUT_OF_DATE = "INDIRECT_OUT_OF_DATE"


class TestStatus(Enum):

    NA = "NA"
    GREEN = "GREEN"
    OUT_OF_DATE = "OUT_OF_DATE"
    INDIRECT_OUT_OF_DATE = "OUT_OF_DATE"
    RED = "RED"
    NO_ENTRY = "NO_ENTRY"


class CdnStatus(Enum):

    NA = "NA"
    SYNC = "SYNC"
    NOT_PUBLISHED = "NOT_PUBLISHED"
    OUT_OF_DATE = "OUT_OF_DATE"
    CDN_ERROR = "CDN_ERROR"


class TargetStatus(NamedTuple):

    target: Package
    src_check_sum: str
    install_status: InstallStatus
    build_status: BuildStatus
    test_status: TestStatus
    cdn_status: CdnStatus
