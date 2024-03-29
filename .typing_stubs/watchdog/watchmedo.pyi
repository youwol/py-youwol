# standard library
from argparse import RawDescriptionHelpFormatter

# third parties
from _typeshed import Incomplete
from watchdog.utils import WatchdogShutdown as WatchdogShutdown
from watchdog.utils import load_class as load_class
from watchdog.version import VERSION_STRING as VERSION_STRING

CONFIG_KEY_TRICKS: str
CONFIG_KEY_PYTHON_PATH: str

class HelpFormatter(RawDescriptionHelpFormatter):
    def __init__(self, *args, max_help_position: int = ..., **kwargs) -> None: ...

epilog: str
cli: Incomplete
subparsers: Incomplete
command_parsers: Incomplete

def argument(*name_or_flags, **kwargs): ...
def command(args=..., parent=..., cmd_aliases=...): ...
def path_split(pathname_spec, separator=...): ...
def add_to_sys_path(pathnames, index: int = ...) -> None: ...
def load_config(tricks_file_pathname): ...
def parse_patterns(patterns_spec, ignore_patterns_spec, separator: str = ...): ...
def observe_with(observer, event_handler, pathnames, recursive) -> None: ...
def schedule_tricks(observer, tricks, pathname, recursive) -> None: ...
def tricks_from(args) -> None: ...
def tricks_generate_yaml(args) -> None: ...
def log(args): ...
def shell_command(args) -> None: ...
def auto_restart(args) -> None: ...

class LogLevelException(Exception): ...

def main(): ...
