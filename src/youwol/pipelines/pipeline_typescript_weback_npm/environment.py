# standard library
from collections.abc import Callable

# third parties
from pydantic import BaseModel

# Youwol pipelines
from youwol.pipelines import CdnTarget
from youwol.pipelines.pipeline_typescript_weback_npm.common.models import NpmRepo


class Environment(BaseModel):
    cdnTargets: list[CdnTarget] = []
    npmTargets: list[NpmRepo] = []


def set_environment(environment: Environment = Environment()):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = Environment


def get_environment() -> Environment:
    return Dependencies.get_environment()
