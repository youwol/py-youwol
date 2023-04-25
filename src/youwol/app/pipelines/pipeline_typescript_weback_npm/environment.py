# typing
from typing import Callable, List

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import UploadTargets

# Youwol pipelines
from youwol.app.pipelines import CdnTarget
from youwol.app.pipelines.pipeline_typescript_weback_npm.common.models import NpmRepo

upload_targets = List[UploadTargets]


class Environment(BaseModel):
    cdnTargets: List[CdnTarget] = []
    npmTargets: List[NpmRepo] = []


def set_environment(environment: Environment = Environment()):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = lambda: Environment()


def get_environment() -> Environment:
    return Dependencies.get_environment()
