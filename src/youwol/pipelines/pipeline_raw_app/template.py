# standard library
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


class Template(NamedTuple):
    name: str


def template(folder: Path) -> ProjectTemplate:
    """
    The template generator entry point.

    This function is typically referenced in your YouWol configuration file to enable the creation
    of new projects directly within the `co-lab` application. For example:

    <code-snippet language='python' highlightedLines="17-19">
    from youwol.app.environment import (
        Configuration,
        ProjectsFinder,
        Projects
    )
    import youwol.pipelines.pipeline_raw_app as pipeline_raw_app

    projects_folder = Path.home() / 'Projects'
    Configuration(
        projects=Projects(
            finder=[
                ProjectsFinder(
                    fromPath=projects_folder,
                    lookUpDepth=1
                ),
            ],
            templates=[
                pipeline_raw_app.template(
                    folder=projects_folder
                )
            ],
        )
    )
    </code-snippet>

    <note level="warning">
    To ensure that a new project can be discovered and loaded via `col-lab`, the projects attribute in YouWol's
    configuration must include a `ProjectsFinder` that covers the folder where the templates are generated.
    </note>

    Parameters:
        folder: The path to the directory where the project skeleton will be created.

    Returns:
        Template generator specification.
    """
    return ProjectTemplate(
        icon={"tag": "img", "src": JS_ICON, "style": {"width": "32px"}},
        type="Raw JS Application",
        folder=folder,
        parameters={
            Keys.name: "Name of the application.",
        },
        generator=lambda _folder, params, context: generate_template(
            folder, params, context
        ),
    )


async def user_inputs_sanity_checks(
    parameters: dict[str, str], context: Context
) -> Template:
    async with context.start("user_inputs_sanity_checks") as ctx:
        if Keys.name not in parameters:
            raise RuntimeError("Expect 'name' in parameters")

        await ctx.info("Required parameters found")

        return Template(name=parameters[Keys.name])


async def generate_template(
    folder: Path, parameters: dict[str, str], context: Context
) -> (str, Path):

    async with context.start("Generate python backend") as ctx:

        inputs = await user_inputs_sanity_checks(parameters, ctx)

        def replace_patterns(file_to_sed: Path):
            for source, replacement in [
                ["application_name", inputs.name],
            ]:
                sed_inplace(file_to_sed, "{{" + source + "}}", replacement)

        folder.mkdir(parents=True, exist_ok=True)

        project_folder = folder / inputs.name

        if project_folder.exists():
            raise RuntimeError(f"Folder {folder} already exist")

        project_folder.mkdir(parents=True)

        src_template_folder = Path(__file__).parent / "template"
        files = [f for f in src_template_folder.glob("**/*") if f.is_file()]
        for file in files:
            dst = (
                project_folder
                / Path(file.parent).relative_to(src_template_folder)
                / file.name
            )
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                src=file,
                dst=dst,
            )
            replace_patterns(dst)

        return parameters["name"], project_folder


JS_ICON = (
    "data:image/png;base64,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"
)
