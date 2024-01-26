"""
This module gathers the service `cdn-backend`.

Responsibilities:
    *  resolve dependencies tree when requesting dependencies installation
    *  serve the resources (e.g. javascript files, css, *etc.*) like a regular CDN


Accessibility:
    *  It is served from the path `/api/cdn-backend`.
    *  In its remote version, it is accessible only via the
        [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/cdn-backend`.

Dependencies:
    *  Dependencies are gathered in the
    [Configuration](@yw-nav-class:youwol.backends.cdn.configurations.Configuration) class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import *
from .router import get_router
