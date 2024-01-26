"""
This module gathers the service `files`.

Responsibilities:
    *  upload and make available single file in the environment. It is only about the 'raw' part of the file here:
    the item in the explorer and the associated asset are created when using the
        [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service.


Accessibility:
    *  It is served from the path `/api/files-backend`.
    *  In its remote version, it is accessible only via the
        [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/files-backend`.

Dependencies:
    *  Dependencies are gathered in the
    [Configuration](@yw-nav-class:youwol.backends.files.configurations.Configuration) class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import *
from .router import get_router
