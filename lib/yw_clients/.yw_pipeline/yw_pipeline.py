# standard library
import re
import tomllib

from pathlib import Path

# Youwol
from youwol import __version__ as yw_version

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.routers.projects import (
    Artifact,
    ExplicitNone,
    Family,
    FileListing,
    Flow,
    IPipelineFactory,
    Link,
    LinkKind,
    Pipeline,
    PipelineStep,
    Project,
    Target,
)

# Youwol utilities
from youwol.utils.context import Context

PYPROJECT_TOML = "pyproject.toml"


def parse_toml(project_folder: Path):
    with open(project_folder / PYPROJECT_TOML, "rb") as f:
        return tomllib.load(f)


dist_files = FileListing(include=["dist/yw_clients-*"])

SRC_FOLDER = "yw_clients/**"


class SetupStep(PipelineStep):

    id = "setup"

    run: ExplicitNone = ExplicitNone()

    sources: FileListing = FileListing(include=[f"../../{PYPROJECT_TOML}"])

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        async with context.start(
            action="SetupStep",
        ):

            def project_name(path):
                return parse_toml(path)["project"]["name"]

            init_file = project.path / project_name(project.path) / "__init__.py"
            with open(init_file, "r", encoding="utf-8") as file:
                content = file.read()

            with open(init_file, "w", encoding="utf-8") as file:
                file.write(
                    re.sub(
                        r"__version__\s*=\s*[\'\"]([^\'\"]*)[\'\"]",
                        f'__version__ = "{yw_version}"',
                        content,
                    )
                )


class BuildStep(PipelineStep):

    id = "build"

    run = "rm -rf ./dist/** && python3 -m build"

    artifacts: list[Artifact] = [Artifact(id="dist", files=dist_files)]
    sources: FileListing = FileListing(include=[SRC_FOLDER, PYPROJECT_TOML])


class CodeQualityStep(PipelineStep):

    id = "quality"

    run = (
        "( cd ../../ && "
        "black lib/yw_clients && "
        "isort lib/yw_clients && "
        "pylint lib/yw_clients &&"
        " mypy lib/yw_clients)"
    )

    sources: FileListing = FileListing(include=[SRC_FOLDER, PYPROJECT_TOML])


class TestStep(PipelineStep):
    id = "test"

    run = "pytest"
    sources: FileListing = FileListing(include=[SRC_FOLDER, "tests/**"])


class PublishStep(PipelineStep):
    """
    Publish into testpypi

    For authentication: provide in your home folder a `.pypirc` file with API token for publication for test.pypi.org,
     e.g.:
    ```
    [distutils]
    index-servers = testpypi

    [testpypi]
    repository: https://test.pypi.org/legacy/
    username = __token__
    password = pypi-***
    ```
    see https://test.pypi.org/help/#apitoken
    """

    id = "publish"

    run = "twine upload --repository testpypi dist/*"

    sources: FileListing = dist_files


async def pipeline(context: Context):
    async with context.start(action="pipeline") as ctx:
        await ctx.info(text="Instantiate pipeline")

        steps = [SetupStep(), BuildStep(), TestStep(), PublishStep(), CodeQualityStep()]

        return Pipeline(
            target=lambda project: Target(
                family=Family.LIBRARY,
                links=[
                    Link(
                        name="PyPi",
                        url="https://pypi.org/",
                        kind=LinkKind.PLAIN_URL,
                    )
                ],
            ),
            tags=["python"],
            projectName=lambda path: parse_toml(path)["project"]["name"],
            projectVersion=lambda path: yw_version,
            steps=steps,
            flows=[
                Flow(
                    name="prod",
                    dag=["setup > test > build > publish", "setup > quality"],
                )
            ],
        )


class PipelineFactory(IPipelineFactory):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get(self, _env: YouwolEnvironment, context: Context) -> Pipeline:
        return await pipeline(context)
