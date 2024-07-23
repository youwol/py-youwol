"""
Child routers of the :mod:`assets-gateway service <youwol.backends.assets_gateway>`.

This page is not well organized, it gathers the endpoints from multiple contributions:
*  Under `api/assets-gateway/cdn-backend` are exposed the endpoints of the
:mod:`cdn <youwol.backends.cdn>` service.
*  Under `api/assets-gateway/assets-backend` are exposed the endpoints of the
:mod:`assets <youwol.backends.assets>`  service.
*  Under `api/assets-gateway/files-backend` are exposed the endpoints of the
:mod:`files <youwol.backends.files>`  service.
*  Under `api/assets-gateway/treedb-backend` are exposed the endpoints of the
:mod:`tree_db <youwol.backends.tree_db>`  service.

The endpoints described here mostly:
*  check authorization
*  forward to the underlying service by adjusting the URL.
*  in case of assets creation or deletion, orchestrate the different required steps.

Please refer to the documentation of the underlying service for detailed description of parameters and returned
response.
"""
