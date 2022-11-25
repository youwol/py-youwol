from typing import Callable, Optional
from dataclasses import dataclass, field
from youwol.pipelines import HelmChartsInstall, DockerRepo


@dataclass(frozen=True)
class Environment:
    docker_target: Optional[DockerRepo] = None
    helm_targets: Optional[HelmChartsInstall] = field(default_factory=lambda: HelmChartsInstall())


def set_environment(environment: Environment):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment]


def get_environment():
    return Dependencies.get_environment()
