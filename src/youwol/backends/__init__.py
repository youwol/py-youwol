"""
This module consolidates the routers (backends) deployed in both the local & online environment
(default: `https://youwol.platform.com`). In local deployments, the backends resolve to their local counterparts,
 while in remote setups, they align with the corresponding remote instances.
 This guarantees uniform behavior for applications exclusively dependent on these backends.

Communication is supported through HTTP calls, with javascript helpers provided by the Typescript project
 [@youwol/http-clients](https://github.com/youwol/http-clients).

**Important**:

For the local YouWol server, all services are exposed directly. However, in the online environment, it is imperative
 to communicate using the `assets-gateway` service (also acting as proxy) for the following services:
  [tree_db](@yw-nav-mod:youwol.backends.tree_db),
  [files](@yw-nav-mod:youwol.backends.files),
  [assets](@yw-nav-mod:youwol.backends.assets), and [cdn](@yw-nav-mod:youwol.backends.cdn).

"""
