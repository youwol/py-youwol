from typing import List

from pydantic import BaseModel

from youwol.configuration.models_base import Check, ErrorResponse
from colorama import Fore, Style


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


class ConfigurationLoadingStatus(BaseModel):

    path: str
    validated: bool = False
    checks: List[Check]


class ConfigurationLoadingException(Exception):

    def __init__(self, status: ConfigurationLoadingStatus):

        self.failed_check = next(check for check in status.checks if isinstance(check.status, ErrorResponse))
        self.status = status

    def __str__(self):
        return f"""{Fore.LIGHTRED_EX}Loading and parsing the configuration file failed{Style.RESET_ALL}.
        The configuration file is located at {self.status.path}
        The first failing step is: 
            {self.failed_check.name}: {Fore.LIGHTYELLOW_EX}{self.failed_check.status.reason}{Style.RESET_ALL}
            hints: {'/n'.join([hint for hint in self.failed_check.status.hints])}
        """
