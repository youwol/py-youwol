# Youwol utilities
from youwol.utils.types import JSON


def patch_files_name(files: list[JSON]):
    """
    When using 'list_files' in storage, the name include the user group, we want to remove it here such that
    we recover the same name as we used first when posting objects
    """
    for file in files:
        if isinstance(file, dict) and "name" in file:
            file["name"] = "/".join(file["name"].split("/")[1:])
    return files
