# typing
from typing import Callable

# third parties
from pydantic import BaseModel

# Youwol pipelines
from youwol.pipelines import DockerRepo, HelmChartsTargets


class Environment(BaseModel):
    dockerTarget: DockerRepo = DockerRepo(
        name="gitlab-docker-repo", host="registry.gitlab.com/youwol/platform"
    )
    helmTargets: HelmChartsTargets = HelmChartsTargets()


def set_environment(environment: Environment):
    Dependencies.get_environment = lambda: environment


class Dependencies:
    get_environment: Callable[[], Environment] = Environment


def get_environment() -> Environment:
    return Dependencies.get_environment()
