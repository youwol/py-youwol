import asyncio
import os
import shutil
import zipfile
from pathlib import Path

from cowpy import cow
from dataclasses import dataclass

from youwol.main_args import get_main_arguments, MainArguments
from youwol.utils_low_level import sed_inplace
from youwol.utils_paths import write_json


@dataclass(frozen=False)
class Configuration:

    starting_yw_config_path: Path
    open_api_prefix: str
    http_port: int
    base_path: str


async def welcome():
    print("""Seems you are a newcomer, Welcome :) 
Just a few post install actions to take care of and you are good to go.""")


async def get_yw_config_starter(main_args: MainArguments):

    if main_args.config_path:
        return main_args.config_path

    # if no config provided by the command line => check if yw_config.py in current folder
    current_folder = main_args.execution_folder
    if (current_folder / 'yw_config.py').exists():
        return current_folder / 'yw_config.py'

    resp = input("No config path has been provided as argument (using --conf),"
                 f" and no yw_config.py file is found in the current folder ({str(current_folder)}).\n"
                 "Do you want to create a new workspace with default settings (y/N)")
    # Ask to create fresh workspace with default settings
    if resp == 'y' or resp == 'Y':

        # create initial databases, at some point we may want to import from an existing one or from a 'store'
        if not (current_folder / 'databases').exists():
            shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'databases.zip',
                            current_folder / 'databases.zip')

            with zipfile.ZipFile(current_folder / 'databases.zip', 'r') as zip_ref:
                zip_ref.extractall(current_folder)

            os.remove(current_folder/'databases.zip')

        # create the default yw_config file
        shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'yw_config.py',
                        current_folder / 'yw_config.py')

        sed_inplace(current_folder / 'yw_config.py', '{{folder_path}}', str(current_folder))

        # create the default identities
        email = input("Your email address?")
        if not (current_folder / 'secrets.json').exists():
            write_json({"identities": {email: "secret not used for now"}}, current_folder / 'secrets.json')
        user_info = {
            "default": email,
            email: {
                "id": "user id not used for now",
                "name": email,
                "memberOf": [
                    "/youwol-users"
                    ],
                "email": email
                }
            }
        if not (current_folder/'users-info.json').exists():
            write_json(user_info, current_folder / 'users-info.json')

        return current_folder / 'yw_config.py'
    else:
        print("Exit youwol")
        exit()


async def get_full_local_config() -> Configuration:

    main_args = get_main_arguments()
    yw_config_path = await get_yw_config_starter(main_args)

    return Configuration(
        starting_yw_config_path=Path(yw_config_path),
        open_api_prefix='',
        http_port=main_args.port,
        base_path=""
        )


configuration: Configuration = asyncio.get_event_loop().run_until_complete(get_full_local_config())


def print_invite(main_args: MainArguments):

    msg = cow.milk_random_cow(f"""
Running with configuration file: {main_args.config_path}

To start youwol please follow this link: 
http://localhost:{main_args.port}/ui/workspace-explorer/

To create and manage assets on your computer please follow this link: 
http://localhost:{main_args.port}/ui/dashboard-developer/
""")
    print(msg)
