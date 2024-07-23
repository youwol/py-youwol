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
  :mod:`tree_db <youwol.backends.tree_db>`,
  :mod:`files <youwol.backends.files>`,
  :mod:`assets <youwol.backends.assets>`, and :mod:`cdn <youwol.backends.cdn>`.

"""
