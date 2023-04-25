# typing
from typing import List

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import (
    Artifact,
    FileListing,
    Link,
    PipelineStep,
)

# Youwol pipelines
from youwol.pipelines.pipeline_typescript_weback_npm.regular.common import Paths

test_result: Artifact = Artifact(
    id="test-result",
    files=FileListing(
        include=["junit.xml"],
    ),
)

test_coverage: Artifact = Artifact(
    id="test-coverage",
    files=FileListing(
        include=["coverage"],
    ),
    links=[Link(name="Coverage", url="coverage/lcov-report/index.html")],
)


class TestStepConfig(BaseModel):
    artifacts: List[Artifact] = [test_result, test_coverage]


class TestStep(PipelineStep):
    id: str
    run: str
    artifacts: List[Artifact]

    sources: FileListing = FileListing(
        include=[Paths.package_json_file, Paths.lib_folder, "src/tests"],
        ignore=[
            Paths.auto_generated_file,
            "**/.*/*",
            "node_modules",
            "**/node_modules",
        ],
    )
