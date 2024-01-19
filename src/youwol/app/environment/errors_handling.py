# standard library
import sys
import traceback

# typing
from typing import Union

# third parties
from colorama import Fore, Style
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    reason: str
    hints: list[str] = []


class Check(BaseModel):
    name: str
    status: Union[bool, ErrorResponse, None] = None


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


class ConfigurationLoadingStatus(BaseModel):
    path: str
    validated: bool = False
    checks: list[Check]


class ConfigurationLoadingException(Exception):
    def __init__(self, status: ConfigurationLoadingStatus):
        self.failed_check = next(
            check for check in status.checks if isinstance(check.status, ErrorResponse)
        )
        self.status = status

    def __str__(self):
        return f"""{Fore.LIGHTRED_EX}Loading and parsing the configuration file failed{Style.RESET_ALL}.
        The configuration file is located at {self.status.path}
        The first failing step is:
            {self.failed_check.name}: {Fore.LIGHTYELLOW_EX}{self.failed_check.status.reason}{Style.RESET_ALL}
            hints: {'/n'.join(self.failed_check.status.hints)}
        """


def format_unknown_error(reason: str, error: Exception):
    detail = error.args[0]
    error_class = error.__class__.__name__
    _, _, tb = sys.exc_info()
    line_number = traceback.extract_tb(tb)[-1][1]
    return ErrorResponse(
        reason=reason, hints=[f"{error_class} at line {line_number}: {detail}"]
    )
