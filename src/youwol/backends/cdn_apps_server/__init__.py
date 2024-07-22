"""
This module gathers the service `cdn_apps_server`.

Responsibilities:
    *  Serves applications from URL with format `/applications/$APP_NAME/$SEMVER_QUERY` by forwarding the requests to
     the service :mod:`cdn-backend <youwol.backends.cdn>` to
     :func:`get the entry point <youwol.backends.cdn.root_paths.get_entry_point>` of
    the corresponding package (through a call to :mod:`assets-gateway <youwol.backends.assets_gateway>`
     regarding permissions).

Accessibility:
    *  It is served from the path `/applications`.
    *  It is directly exposed in remote environment.

Dependencies:
    *  Dependencies are gathered in the
    :class:`Configuration <youwol.backends.cdn_apps_server.configurations.Configuration>` class.
"""

# relative
from .configurations import Configuration, Dependencies
from .root_paths import *
from .router import get_router
