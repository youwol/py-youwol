"""
This module defines the [HTTP API router](https://fastapi.tiangolo.com/reference/apirouter/?h=apir) regarding
  management of projects, it is served from the base HTTP URL: `/admin/projects`

"""

# relative
from .dependencies import *
from .implementation import *
from .models import *
from .models_project import *
from .projects_loader import *
