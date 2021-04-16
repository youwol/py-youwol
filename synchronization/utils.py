import json
import os
from pathlib import Path


def create_empty_dbs(system_path: Path):

    dst_databases = system_path / 'databases'

    folders = [
        dst_databases/'docdb'/'cdn'/'libraries',
        dst_databases/'docdb'/'tree_db'/'drives',
        dst_databases/'docdb'/'tree_db'/'folders',
        dst_databases/'docdb'/'tree_db'/'items',
        dst_databases/'docdb'/'tree_db'/'deleted',
        dst_databases/'docdb'/'assets'/'access_history',
        dst_databases/'docdb'/'assets'/'access_policy',
        dst_databases/'docdb'/'assets'/'entities',
        dst_databases/'docdb'/'flux'/'component',
        dst_databases/'docdb'/'flux'/'projects',
        dst_databases/'docdb'/'flux'/'entities'
        ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        with open(folder/'data.json', 'w') as file:
            json.dump({"documents": []}, file, indent=4)
