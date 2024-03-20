# standard library
from pathlib import Path

# third parties
from pydantic import BaseModel


class Failure(BaseModel):
    """
    Base class of project loading failures.
    """

    path: Path
    """
    Project folder's path.
    """
    failure: str = "generic"
    """
    Failure type.
    """
    message: str
    """
    Message.
    """


class FailurePipelineNotFound(Failure):
    """
    Failure because of a directory not found.
    """

    failure: str = "pipeline_not_found"
    """
    Failure type.
    """
    message: str = "Pipeline `.yw_pipeline/yw_pipeline.py` not found"
    """
    Message.
    """


class FailureDirectoryNotFound(Failure):
    """
    Failure because of a `yw_pipeline.py` file not found.
    """

    failure: str = "directory_not_found"
    """
    Failure type.
    """
    message: str = "Project's directory not found"
    """
    Message.
    """


class FailureImportException(Failure):
    """
    Failure because of an exception while parsing `yw_pipeline.py`.
    """

    failure: str = "import"
    """
    Failure type.
    """
    traceback: str
    """
    Traceback of the exception.
    """
    exceptionType: str
    """
    Exception type.
    """
