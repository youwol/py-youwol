# standard library
import re
import shutil

from pathlib import Path

# typing
from typing import NamedTuple

# Youwol application
from youwol.app.environment import ProjectTemplate

# Youwol utilities
from youwol.utils import Context, sed_inplace


class Keys(NamedTuple):
    name = "name"
    port = "port"


def template(folder: Path) -> ProjectTemplate:
    """
    Template generator specification for a basic project.

    Example:
        It can be referenced in your configuration like this:
        ```python
        from youwol.app.environment import (
            Configuration,
            Projects,
            RecursiveProjectsFinder
        )
        from youwol.pipelines.pipeline_python_backend import template

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=RecursiveProjectsFinder(
                    fromPaths=[projects_folder],
                ),
                templates=[template(folder=projects_folder / 'auto-generated')],
            )
        )
        ```

        Generation of a new project is then triggered through the developer portal applications.

    Parameters:
        folder: path of the folder in which templates are added.

    Return:
        Project's template specification.
    """
    return ProjectTemplate(
        icon={"tag": "img", "src": pyIcon},
        type="python backend",
        folder=folder,
        parameters={
            Keys.name: "Name of the service.",
            Keys.port: "Default port to serve.",
        },
        generator=lambda _folder, params, context: generate_template(
            folder, params, context
        ),
    )


class Template(NamedTuple):
    name: str
    port: int


async def user_inputs_sanity_checks(
    parameters: dict[str, str], context: Context
) -> Template:
    def is_valid_python_package_name(name: str) -> bool:
        pattern = r"^[a-zA-Z_]\w*$"
        return bool(re.match(pattern, name))

    async with context.start("user_inputs_sanity_checks") as ctx:
        if Keys.name not in parameters:
            raise RuntimeError("Expect 'name' in parameters")

        if Keys.port not in parameters:
            raise RuntimeError("Expect 'port' in parameters")

        await ctx.info("Required parameters found")

        if not is_valid_python_package_name(Keys.name):
            raise RuntimeError("The name provide does not adhere to PEP 8 convention.")

        port = int(parameters[Keys.port])
        return Template(name=parameters[Keys.name], port=port)


async def generate_template(folder: Path, parameters: dict[str, str], context: Context):
    async with context.start("Generate python backend") as ctx:
        inputs = await user_inputs_sanity_checks(parameters, ctx)

        def replace_patterns(file_to_sed: Path):
            for source, replacement in [
                ["package_name", inputs.name],
                ["default_port", str(inputs.port)],
            ]:
                sed_inplace(file_to_sed, "{{" + source + "}}", replacement)

        folder.mkdir(parents=True, exist_ok=True)

        project_folder = folder / f"{inputs.name}_project"
        if project_folder.exists():
            raise RuntimeError(f"Folder {folder} already exist")

        project_folder.mkdir(parents=True)

        package_folder = project_folder / inputs.name
        package_folder.mkdir(parents=True)

        files = (Path(__file__).parent / "template" / "src").glob("**/*")
        for file in files:
            dst = package_folder / file.name.replace(".txt", "")
            shutil.copyfile(
                src=file,
                dst=package_folder / file.name.replace(".txt", ""),
            )
            replace_patterns(dst)

        shutil.copytree(
            src=Path(__file__).parent / "template" / ".yw_pipeline",
            dst=project_folder / ".yw_pipeline",
        )
        shutil.copyfile(
            src=Path(__file__).parent / "template" / "pyproject.toml.txt",
            dst=project_folder / "pyproject.toml",
        )

        replace_patterns(project_folder / "pyproject.toml")

        return parameters["name"], folder


pyIcon = (
    "data:image/png;base64,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"
)
