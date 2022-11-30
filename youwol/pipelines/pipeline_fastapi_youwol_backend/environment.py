from typing import Callable, Optional

from pydantic import BaseModel
from youwol.pipelines import HelmChartsTargets, DockerRepo


class Environment(BaseModel):
    dockerTarget: Optional[DockerRepo]
    helmTargets: HelmChartsTargets = HelmChartsTargets()


def set_environment(environment: Environment):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment]


def get_environment() -> Environment:
    return Dependencies.get_environment()
