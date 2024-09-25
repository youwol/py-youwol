"""
This file gathers models involved in
:class:`YouwolEnvironment <youwol.app.environment.youwol_environment.YouwolEnvironment>` that are not already part of
 the module :mod:`environment.models <youwol.app.environment.models>`.
"""

# standard library
import importlib

from pathlib import Path

# third parties
from pydantic import BaseModel

# relative
from .models.defaults import default_path_projects_dir
from .models.models_config import ConfigPath
from .models.models_config import Projects as ConfigProjects
from .models.models_project import ProjectsFinder, ProjectTemplate


class ProjectsResolver(BaseModel):
    """
    Facilitates the discovery and organization of projects by utilizing a combination of
    finders and templates.
    The finders are responsible for locating project directories based on certain criteria,
    while the templates provide scaffolding for new projects.

    It is a straightforward normalization of the
    :class:`Projects <youwol.app.environment.models.models_project.Projects>`
    configuration's model.
    """

    finders: list[ProjectsFinder] = []
    """
    Each element of the list is responsible for locating project directories based on certain criteria.
    """
    templates: list[ProjectTemplate] = []
    """
    Each element of the list provides scaffolding for new projects of particular kind.
    """

    @staticmethod
    def from_configuration(config_projects: ConfigProjects | None):
        """
        Normalizes the :attr:`Projects.finder <youwol.app.environment.models.models_project.Projects.finder>`
        attribute from the configuration to set the
        :attr:`YouwolEnvironment.projects <youwol.app.environment.youwol_environment.YouwolEnvironment.projects>`
        attribute.

        Parameters:
            config_projects: Projects as defined in the configuration.
        """

        def convert(finder: ProjectsFinder | ConfigPath):
            if isinstance(config_projects.finder, (str, Path)):
                return ProjectsFinder(fromPath=finder)
            return finder

        if not config_projects:
            config_projects = get_default_projects_configuration()

        if isinstance(config_projects.finder, (str, Path, ProjectsFinder)):
            finders = [convert(config_projects.finder)]
        else:
            finders = [convert(f) for f in config_projects.finder]

        return ProjectsResolver(finders=finders, templates=config_projects.templates)


def get_default_projects_configuration() -> ConfigProjects:
    """
    Construct and returns the default configuration for projects used in
    :class:`Configuration <youwol.app.environment.models.models_config.Configuration>` if none has been provided.

    It combines a default :class:`ProjectsFinder<youwol.app.environment.models.models_project.ProjectsFinder>` with
    a couple of usual projects template provided by YouWol (see :mod:`pipelines <youwol.pipelines>`).

    Returns:
        The default project's configuration.
    """
    # Why not use the usual import at the top of the file?
    # => This approach is a workaround to avoid cyclic dependencies between YouWol's environment and YouWol's pipeline.
    #    Typically, templates are added via the configuration file, which works well since it is external to YouWol
    #    itself.
    #
    # Why not use `import youwol.pipelines.pipeline_raw_app as raw_pipeline`?
    # => This avoids numerous warnings and errors from pylint and other linters.
    #
    # Although not perfect, this solution offers newcomers a smoother experience when getting started with YouWol.

    raw_pipeline = importlib.import_module("youwol.pipelines.pipeline_raw_app")
    ts_pipeline = importlib.import_module(
        "youwol.pipelines.pipeline_typescript_weback_npm.regular"
    )
    pybackend_pipeline = importlib.import_module(
        "youwol.pipelines.pipeline_python_backend"
    )

    return ConfigProjects(
        templates=[
            raw_pipeline.template(folder=default_path_projects_dir),
            ts_pipeline.app_ts_webpack_template(folder=default_path_projects_dir),
            ts_pipeline.lib_ts_webpack_template(folder=default_path_projects_dir),
            pybackend_pipeline.template(folder=default_path_projects_dir),
        ]
    )
