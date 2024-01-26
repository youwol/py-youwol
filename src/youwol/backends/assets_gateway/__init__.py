"""
This module gathers the service `assets_gateway`.

Responsibilities:
    *  ensures permissions before accessing/creating/deleting assets and related data.
    *  orchestrates creation and deletion of asset.
    *  proxies the services [tree_db](@yw-nav-mod:youwol.backends.tree_db),
    [assets](@yw-nav-mod:youwol.backends.assets), [cdn](@yw-nav-mod:youwol.backends.cdn),
    [files](@yw-nav-mod:youwol.backends.files). Those are not exposed in
    remote environment.

    **Note**:
        In youwol, an asset is always associated to an entry in the
        [tree_db](@yw-nav-mod:youwol.backends.tree_db) and
        [assets](@yw-nav-mod:youwol.backends.assets) services.
        Eventually, for assets of `kind=='package'` or `kind=='data'`, it is also associated to an entry in the
        [cdn](@yw-nav-mod:youwol.backends.cdn) and  [files](@yw-nav-mod:youwol.backends.files) services respectively.
        In these cases, the `rawId` attribute of an asset
        corresponds to the ID of the corresponding entity in the services.

    **Warnings**:
        Event though all services are exposed directly in the local server, the usage of the services
         [tree_db](@yw-nav-mod:youwol.backends.tree_db),
        [files](@yw-nav-mod:youwol.backends.files), [assets](@yw-nav-mod:youwol.backends.assets) and
        [cdn](@yw-nav-mod:youwol.backends.cdn) is only safe when accessed through the `assets-gateway` service.
        Direct access in local is: (i) **not portable**: those calls are prohibited in remote environment
         and (ii) **dangerous**: `assets-gateway` has a role of orchestrator in multiple contexts.


Accessibility:
    *  It is served from the path `/api/assets-gateway`.
    *  It is directly exposed in remote environment.

Dependencies:
    *  Dependencies are gathered in the
    [Configuration](@yw-nav-class:youwol.backends.assets_gateway.configurations.Configuration) class.
"""

# relative
from .configurations import Configuration, Dependencies
from .root_paths import router
from .router import get_router
