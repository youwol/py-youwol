"""
This module gathers the service `assets`.

Responsibilities:
    *  Manage metadata of assets (images, name, description, *etc.*).
    *  Manage the files associated to assets.
    *  Manage access policies and permissions of assets.

Accessibility:
    *  It is served from the path `/api/assets-backend`.
    *  In its remote version, it is accessible only via the
        :mod:`assets_gatewayr <youwol.backends.assets_gateway>` service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/assets-backend`.

Dependencies:
    *  Dependencies are gathered in the
    :class:`Configuration <youwol.backends.assets.configurations.Configuration>` class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .router import get_router
