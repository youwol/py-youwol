# standard library
from collections.abc import Callable

# Youwol pipelines
from youwol.pipelines import Environment as CdnBaseEnv
from youwol.pipelines.pipeline_typescript_weback_npm.common.models import (
    NpmRepo,
    PublicNpmRepo,
)


class Environment(CdnBaseEnv):
    npmTargets: list[NpmRepo] = [PublicNpmRepo(name="public")]


def set_environment(environment: Environment = Environment()):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = Environment


def get_environment() -> Environment:
    return Dependencies.get_environment()
