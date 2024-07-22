"""
This module gathers the service `assets_gateway`.

Responsibilities:
    *  ensures permissions before accessing/creating/deleting assets and related data.
    *  orchestrates creation and deletion of asset.
    *  proxies the services :mod:`tree_db <youwol.backends.tree_db>`,
    :mod:`assets <youwol.backends.assets>`, :mod:`cdn <youwol.backends.cdn>`,
    :mod:`files <youwol.backends.files>`. Those are not exposed in
    remote environment.

    **Note**:
        In youwol, an asset is always associated to an entry in the
        :mod:`tree_db <youwol.backends.tree_db>` and
        :mod:`assets <youwol.backends.assets>` services.
        Eventually, for assets of `kind=='package'` or `kind=='data'`, it is also associated to an entry in the
        :mod:`cdn <youwol.backends.cdn>`  and  :mod:`files <youwol.backends.files>`  services respectively.
        In these cases, the `rawId` attribute of an asset
        corresponds to the ID of the corresponding entity in the services.

    **Warnings**:
        Event though all services are exposed directly in the local server, the usage of the services
         :mod:`tree_db <youwol.backends.tree_db>`,
        :mod:`files <youwol.backends.files>`, :mod:`assets <youwol.backends.assets>` and
        :mod:`cdn <youwol.backends.cdn>` is only safe when accessed through the `assets-gateway` service.
        Direct access in local is: (i) **not portable**: those calls are prohibited in remote environment
         and (ii) **dangerous**: `assets-gateway` has a role of orchestrator in multiple contexts.


Accessibility:
    *  It is served from the path `/api/assets-gateway`.
    *  It is directly exposed in remote environment.

Dependencies:
    *  Dependencies are gathered in the
    :class:`Configuration <youwol.backends.assets_gateway.configurations.Configuration>` class.
"""

# relative
from .configurations import Configuration, Dependencies
from .root_paths import router
from .router import get_router
