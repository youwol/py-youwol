# standard library
import argparse
import os

from pathlib import Path

# typing
from typing import NamedTuple, Optional

parser = argparse.ArgumentParser()

parser.add_argument("--daemonize", help="Daemonize", action="store_true")
parser.add_argument("--port", help="Specify the port")
parser.add_argument("--conf", help="Path to a configuration file")
parser.add_argument(
    "--email", help="Email of the user - should be referenced in users-info.json"
)
parser.add_argument(
    "--verbose", help='Configure uvicorn logging to "info"', action="store_true"
)
parser.add_argument(
    "--init",
    help="Initialize configuration if the configuration path does not exists",
    action="store_true",
)

args = parser.parse_args()


class MainArguments(NamedTuple):
    """
    Optional arguments that can be set when starting youwol.

    Inline help for arguments description can be displayed using:
    ```shell
    youwol --help
    ```
    """

    port: int
    """
    Specify the port, exposed as **--port**.

    **Example**
    ```shell
    youwol --port=2003
    ```
    """
    config_path: Path
    """
    Path to the configuration file, exposed as **--conf**.

    **Example**
    ```shell
    youwol --conf='~/Projects/youwol/configuration.py'
    ```
    """

    daemonize: bool = False
    """
    Whether to run youwol in [daemonized](https://en.wikipedia.org/wiki/Daemon_(computing)) mode,
     exposed as **--daemonize**.

    **Example**
    ```shell
    youwol --daemonize=true
    ```
    """
    email: Optional[str] = None

    execution_folder = Path(os.getcwd())
    verbose: bool = False
    """
    Configure uvicorn logging to "info", exposed as **--verbose**.

    **Example**
    ```shell
    youwol --verbose=true
    ```
    """

    init: bool = False


def get_main_arguments() -> MainArguments:
    return MainArguments(
        port=int(args.port) if args.port else 2000,
        config_path=Path(args.conf) if args.conf else None,
        email=args.email if args.email else None,
        daemonize=args.daemonize if args.daemonize else False,
        verbose=args.verbose if args.verbose else False,
        init=args.init if args.init else False,
    )
