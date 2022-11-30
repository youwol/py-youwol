from typing import Callable

from pydantic import BaseModel
from youwol.pipelines import HelmChartsTargets, DockerRepo


class Environment(BaseModel):
    dockerTarget: DockerRepo = DockerRepo(
        name="gitlab-docker-repo",
        host="registry.gitlab.com/youwol/platform"
    )
    helmTargets: HelmChartsTargets = HelmChartsTargets()


def set_environment(environment: Environment):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = lambda: Environment()


def get_environment() -> Environment:
    return Dependencies.get_environment()
