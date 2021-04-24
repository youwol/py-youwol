from typing import List

from pydantic import BaseModel

from youwol.configuration.models_base import Check, ErrorResponse
from youwol.errors import HTTPResponseException


class CheckConfPath(Check):
    name: str = "Configuration path exist?"


class CheckValidTextFile(Check):
    name: str = "Valid text file?"


class CheckValidPythonScript(Check):
    name: str = "Valid python script?"


class CheckValidConfigParametersFunction(Check):
    name: str = "configuration_parameters function valid?"


class CheckValidConfigurationFunction(Check):
    name: str = "Configuration function valid?"


class CheckSystemFolderWritable(Check):
    name: str = "System folder is writable?"


class CheckDatabasesFolderHealthy(Check):
    name: str = "Databases folder is healthy?"


class CheckSecretPathExist(Check):
    name: str = "Secrets path is valid?"


class CheckSecretHealthy(Check):
    name: str = "Secrets are valid?"


class CheckDefaultPublishPath(Check):
    name: str = "Default publish path is valid?"


class ConfigurationLoadingStatus(BaseModel):

    path: str
    validated: bool = False
    checks: List[Check]


class ConfigurationLoadingException(HTTPResponseException):

    def __init__(self, status: ConfigurationLoadingStatus):

        check = next(check for check in status.checks if isinstance(check.status, ErrorResponse))
        super().__init__(
            status_code=500,
            title=check.name,
            descriptions=[
                "Loading and parsing the configuration file failed.",
                f"Path of the config file: {status.path}"
                ],
            hints=check.status.hints,
            footer="Try reloading the page after the issue resolution")
        self.status = status
