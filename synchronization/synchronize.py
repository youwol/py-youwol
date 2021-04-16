import os
import shutil
from pathlib import Path

from synchronization.assets import copy_assets
from synchronization.cdn import sync_cdn
from synchronization.data import sync_data
from synchronization.services import sync_services
from synchronization.utils import create_empty_dbs


platform_path = Path("/home/greinisch/Projects/platform/")
system_path = Path(os.path.realpath(__file__)).parent.parent/"youwol_data"
if (system_path/'databases').exists():
    shutil.rmtree(system_path/'databases')

sync_services(platform_path)
create_empty_dbs(system_path)
sync_cdn(platform_path, system_path)
sync_data(system_path)

copy_assets(platform_path, system_path)

################
# Packaging .zip
################

shutil.make_archive(system_path / 'databases', 'zip', system_path, base_dir='databases')
if (system_path/'databases').exists():
    shutil.rmtree(system_path/'databases')
