import argparse
import os
from pathlib import Path
from typing import NamedTuple, Optional

import youwol

parser = argparse.ArgumentParser()

parser.add_argument('--daemonize', help='Daemonize', action="store_true")
parser.add_argument('--port', help='Specify the port')
parser.add_argument('--conf', help='Path to a configuration file')
parser.add_argument('--email', help='Email of the user - should be referenced in users-info.json')
parser.add_argument('--profile', help='Configuration profile to load')
parser.add_argument('--verbose', help='Configure uvicorn logging to "info"', action="store_true")

args = parser.parse_args()


class MainArguments(NamedTuple):
    port: int
    config_path: Path
    daemonize: bool = False
    profile: Optional[str] = None
    email: Optional[str] = None
    youwol_path: Path = Path(youwol.__file__).parent
    system_path = youwol_path.parent / "youwol_data"
    execution_folder = Path(os.getcwd())
    verbose: bool = False


def get_main_arguments() -> MainArguments:
    return MainArguments(
        port=int(args.port) if args.port else 2000,
        config_path=Path(args.conf) if args.conf else None,
        email=args.email if args.email else None,
        profile=args.profile if args.profile else None,
        daemonize=args.daemonize if args.daemonize else False,
        verbose=args.verbose if args.verbose else False

    )
