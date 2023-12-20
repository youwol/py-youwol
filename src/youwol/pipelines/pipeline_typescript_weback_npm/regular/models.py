# standard library
from pathlib import Path

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.routers.projects.models_project import Project


class InputDataDependency(BaseModel):
    project: Project
    dist_folder: Path
    src_folder: Path
    dist_files: list[Path]
    src_files: list[Path]
    checksum: str
