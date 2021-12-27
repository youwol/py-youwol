from inspect import signature
from pathlib import Path

from pydantic import BaseModel

from youwol.configuration import ErrorResponse, format_unknown_error
from youwol.configuration.configuration_validation import ConfigurationLoadingStatus, CheckConfPath, CheckValidTextFile, \
    CheckValidPythonScript, CheckValidConfigurationFunction, ConfigurationLoadingException


class PythonSourceFunction(BaseModel):
    path: Path
    name: str


def get_python_function(source_function : PythonSourceFunction):

    check_conf_path = CheckConfPath()
    check_valid_text = CheckValidTextFile()
    check_valid_python = CheckValidPythonScript()
    check_valid_conf_fct = CheckValidConfigurationFunction()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(source_function.path),
            validated=validated,
            checks=[
                check_conf_path,
                check_valid_text,
                check_valid_python,
                check_valid_conf_fct,
            ]
        )
    if not source_function.path.exists():
        check_conf_path.status = ErrorResponse(
            reason="The specified configuration path does not exist.",
            hints=[f"Double check the location '{str(source_function.path)}' do exist."]
        )
        raise ConfigurationLoadingException(get_status(False))

    check_conf_path.status = True
    try:
        source = Path(source_function.path).read_text()
    except Exception as e:
        print(e)
        check_valid_text.status = ErrorResponse(
            reason="The specified configuration path is not a valid text file.",
            hints=[f"Double check the file at location '{str(source_function.path)}' is a valid text file."]
        )
        raise ConfigurationLoadingException(get_status(False))

    check_valid_text.status = True
    try:
        scope = {}
        exec(source, scope)
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno
        check_valid_python.status = ErrorResponse(
            reason=f"There is a syntax error in the python file.",
            hints=[f"{error_class} at line {line_number}: {detail}"]
        )
        raise ConfigurationLoadingException(get_status(False))
    except Exception as err:
        check_valid_python.status = format_unknown_error(
            reason=f"There was an exception parsing your python file.",
            error=err)
        raise ConfigurationLoadingException(get_status(False))

    check_valid_python.status = True

    if source_function.name not in scope:
        check_valid_conf_fct.status = ErrorResponse(
            reason=f"The configuration file need to define a '{source_function.name}' function.",
            hints=[f"""Make sure the configuration file include a function with signature :
                'async def configuration(main_args: MainArguments)."""])
        raise ConfigurationLoadingException(get_status(False))

    fn = scope[source_function.name]

    sig = signature(fn)

    return scope[source_function.name]
