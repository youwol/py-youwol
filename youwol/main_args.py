import argparse
import os
from pathlib import Path
from typing import NamedTuple
import youwol

parser = argparse.ArgumentParser()

parser.add_argument('--port', help='Specify the port')
parser.add_argument('--conf', help='Path to a configuration file')

args = parser.parse_args()


class MainArguments(NamedTuple):
    port: int
    config_path: Path
    youwol_path: Path = Path(youwol.__file__).parent
    system_path = youwol_path.parent / "youwol_data"
    execution_folder = Path(os.getcwd())


def get_main_arguments() -> MainArguments:
    return MainArguments(
        port=int(args.port) if args.port else 2000,
        config_path=Path(args.conf) if args.conf else None
        )
