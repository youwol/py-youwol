from pathlib import Path
from typing import List

from pydantic import BaseModel

from youwol.environment.models_project import Project


class InputDataDependency(BaseModel):
    project: Project
    dist_folder: Path
    src_folder: Path
    dist_files: List[Path]
    src_files: List[Path]
    checksum: str
