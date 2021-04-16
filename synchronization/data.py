import json
import os
from pathlib import Path


def sync_data(system_path: Path):

    db_path = system_path / 'databases' / 'docdb' / 'data' / 'entities' / 'data.json'
    os.makedirs(db_path.parent)
    with open(db_path, 'w') as file:
        json.dump({"documents": []}, file, indent=4)
