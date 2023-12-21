"""
This module defines the [HTTP API router](https://fastapi.tiangolo.com/reference/apirouter/?h=apir) regarding
  management of the environment, it is served from the base HTTP URL:

> **`/admin/environment`**

"""

# relative
from .download_assets import *
from .models import *
from .upload_assets import *
