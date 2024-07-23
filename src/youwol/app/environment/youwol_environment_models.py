"""
This file gathers models involved in
:class:`YouwolEnvironment <youwol.app.environment.youwol_environment.YouwolEnvironment>` that are not already part of
 the module :mod:`environment.models <youwol.app.environment.models>`.
"""

# standard library
from pathlib import Path

# third parties
from pydantic import BaseModel

# relative
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
    def from_configuration(config_projects: ConfigProjects):
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

        if isinstance(config_projects.finder, (str, Path, ProjectsFinder)):
            finders = [convert(config_projects.finder)]
        else:
            finders = [convert(f) for f in config_projects.finder]

        return ProjectsResolver(finders=finders, templates=config_projects.templates)
