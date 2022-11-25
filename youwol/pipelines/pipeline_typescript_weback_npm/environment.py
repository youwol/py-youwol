from typing import List, Callable
from dataclasses import dataclass, field

from youwol.configuration.models_config import UploadTargets
from youwol.pipelines import YwPlatformTarget
from youwol.pipelines.pipeline_typescript_weback_npm.common.models import NpmRepo

upload_targets = List[UploadTargets]


@dataclass(frozen=True)
class Environment:
    cdn_targets: List[YwPlatformTarget] = field(default_factory=lambda: [])
    npm_targets: List[NpmRepo] = field(default_factory=lambda: [])


def set_environment(environment: Environment = Environment(cdn_targets=[], npm_targets=[])):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment]


def get_environment():
    return Dependencies.get_environment()
