import os
from pathlib import Path

from youwol.configuration.models_base import Check, ErrorResponse


def _check_package_name(name: str, check: Check):

    if " " in name:
        check.status = ErrorResponse(
            reason="No space allowed in package name",
            hints=[f"See https://docs.npmjs.com/creating-a-package-json-file"]
            )
        return
    if not name.lower() == name:
        check.status = ErrorResponse(
            reason="No upper case allowed in name",
            hints=[f"See https://docs.npmjs.com/creating-a-package-json-file"]
            )
        return
    check.status = True


def _check_destination_folder(folder: Path, check: Check):

    if not folder.parent.exists():
        check.status = ErrorResponse(
            reason=f"Parent folder do not exist: ({str(folder.parent)})",
            hints=["Make sure you provide the correct folder path in your configuration"]
            )
        return

    if folder.exists():
        check.status = ErrorResponse(
            reason=f"Folder already exists ({str(folder)})",
            hints=["Change your package name, or remove the existing one"]
            )
        return

    if not os.access(folder.parent, os.W_OK):
        check.status = ErrorResponse(
            reason=f"Can not write in folder {str(folder.parent)}",
            hints=[f"Ensure you have permission to write in {folder.parent}."]
            )
        return

    check.status = True
