import asyncio
import os
import sys
import shutil
import zipfile
from getpass import getpass
from pathlib import Path

from fastapi import HTTPException
from cowpy import cow
from dataclasses import dataclass

from youwol.configuration import get_public_user_auth_token, YouwolConfiguration
from youwol.main_args import get_main_arguments, MainArguments
from youwol.utils_low_level import sed_inplace
from youwol.utils_paths import write_json
from youwol_utils import retrieve_user_info

from colorama import Fore, Style


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
    if not (resp == 'y' or resp == 'Y'):
        print("Exit youwol")
        exit()

    # create the default identities
    email = input("Your email address?")
    pwd = getpass("Your YouWol password?")
    token = None
    default_openid_host = "gc.auth.youwol.com"
    try:
        token = await get_public_user_auth_token(username=email, pwd=pwd, client_id='public-user',
                                                 openid_host=default_openid_host)
        print("token", token)
    except HTTPException as e:
        print(f"Can not retrieve authentication token:\n\tstatus code: {e.status_code}\n\tdetail:{e.detail}")
        exit(1)

    user_info = None
    try:
        user_info = await retrieve_user_info(auth_token=token, openid_host=default_openid_host)
        print("user_info", user_info)
    except HTTPException as e:
        print(f"Can not retrieve user info:\n\tstatus code: {e.status_code}\n\tdetail:{e.detail}")
        exit(1)
    # create initial databases, at some point we may want to import from an existing one or from a 'store'
    if not (current_folder / 'databases').exists():
        shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'databases.zip',
                        current_folder / 'databases.zip')

        with zipfile.ZipFile(current_folder / 'databases.zip', 'r') as zip_ref:
            zip_ref.extractall(current_folder)

        os.remove(current_folder / 'databases.zip')

    # create the default yw_config file
    shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'yw_config.py',
                    current_folder / 'yw_config.py')
    shutil.copyfile(main_args.youwol_path.parent / 'youwol_data' / 'remotes-info.json',
                    current_folder / 'remotes-info.json')

    sed_inplace(current_folder / 'yw_config.py', '{{folder_path}}', str(current_folder))

    if not (current_folder / 'secrets.json').exists():
        write_json({email: {'password': pwd}}, current_folder / 'secrets.json')

    user_info = {
        "policies": {"default": email},
        "users": {
            email: {
                "id": user_info['sub'],
                "name": user_info['name'],
                "memberOf": user_info['memberof'],
                "email": user_info['email']
                }
            }
        }

    if not (current_folder/'users-info.json').exists():
        write_json(user_info, current_folder / 'users-info.json')

    return current_folder / 'yw_config.py'


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


def assert_python():

    print(f"Running with python:\n\t{sys.executable}\n\t{sys.version}")
    version_info = sys.version_info
    if not ((version_info.major == 3 and version_info.minor == 10) or
            (version_info.major == 3 and version_info.minor == 9) or
            (version_info.major == 3 and version_info.minor == 8) or
            (version_info.major == 3 and version_info.minor == 7) or
            (version_info.major == 3 and version_info.minor == 6)):
        print(f"""Your version of python is not compatible with py-youwol:
        Required: 3.9.x""")
        exit(1)


def print_invite(main_args: MainArguments, conf: YouwolConfiguration):

    print(f"""{Fore.GREEN} Configuration loaded successfully {Style.RESET_ALL}.
""")
    print(conf)
    msg = cow.milk_random_cow(f"""
All good, you can now browse to
http://localhost:{conf.http_port}/applications/@youwol/workspace-explorer/latest
""")
    print(msg)
