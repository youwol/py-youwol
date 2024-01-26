"""
This module gathers the service `cdn_sessions_storage`.

Responsibilities:
    *  Allows an application to persist arbitrary JSON user data.

Accessibility:
    *  It is served from the path `/api/cdn-sessions-storage`.
    *  It is directly exposed in remote environment.

Dependencies:
    *  Dependencies are gathered in the
    [Configuration](@yw-nav-class:youwol.backends.cdn_apps_server.configurations.Configuration) class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import *
from .router import get_router
