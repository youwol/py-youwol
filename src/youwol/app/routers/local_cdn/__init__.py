"""
This module defines the [HTTP API router](https://fastapi.tiangolo.com/reference/apirouter/?h=apir) regarding
  management of the local CDN (regarding the components), it is served from the base HTTP URL:

> **`/admin/local-cdn`**

"""

# relative
from .implementation import *
from .models import *
