"""
This module gathers the service `files`.

Responsibilities:
    *  upload and make available single file in the environment. It is only about the 'raw' part of the file here:
    the item in the explorer and the associated asset are created when using the
        :mod:`assets_gateway <youwol.backends.assets_gateway>` service.


Accessibility:
    *  It is served from the path `/api/files-backend`.
    *  In its remote version, it is accessible only via the
        :mod:`assets_gateway <youwol.backends.assets_gateway>` service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/files-backend`.

Dependencies:
    *  Dependencies are gathered in the
    :class:`Configuration <youwol.backends.files.configurations.Configuration>` class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import *
from .router import get_router
