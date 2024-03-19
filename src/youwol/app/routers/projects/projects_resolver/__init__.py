"""
This module gathers implementation to locate and resolve projects within the user's hard drive.

The usual entry point is [ProjectLoader](@yw-nav-class:ProjectLoader), details on locating projects are encapsulated
from [ProjectsFinderImpl](@yw-nav-class:ProjectsFinderImpl).

The specification of the look-up strategy is defined from the configuration file through the
[ProjectsFinder](@yw-nav-class:ProjectsFinder) model.

Project loading errors are defined from the class [Failure](@yw-nav-class:projects_resolver.models.Failure).
"""

# relative
from .models import *
from .projects_loader import *
