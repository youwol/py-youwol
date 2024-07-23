"""
This module gathers implementation to locate and resolve projects within the user's hard drive.

The usual entry point is
:class:`ProjectLoader <youwol.app.routers.projects.projects_resolver.projects_loader.ProjectLoader>`,
details on locating projects are encapsulated from
:class:`ProjectsFinderImpl <youwol.app.routers.projects.projects_resolver.projects_finder_handlers.ProjectsFinderImpl>`.

The specification of the look-up strategy is defined from the configuration file through the
:class:`ProjectsFinder <youwol.app.environment.models.models_project.ProjectsFinder>` model.

Project loading errors are defined from the class
:class:`Failure <youwol.app.routers.projects.projects_resolver.models.Failure>`.
"""

# relative
from .models import *
from .projects_loader import *
