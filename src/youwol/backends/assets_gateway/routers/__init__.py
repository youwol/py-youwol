"""
Child routers of the [assets-gateway service](@yw-nav-mod:backends.assets_gateway).

This page is not well organized, it gathers the endpoints from multiple contributions:
*  Under `api/assets-gateway/cdn-backend` are exposed the endpoints of the
[cdn-backend](@yw-nav-mod:backends.cdn) service.
*  Under `api/assets-gateway/assets-backend` are exposed the endpoints of the
[assets-backend](@yw-nav-mod:backends.assets) service.
*  Under `api/assets-gateway/files-backend` are exposed the endpoints of the
[files-backend](@yw-nav-mod:backends.files) service.
*  Under `api/assets-gateway/treedb-backend` are exposed the endpoints of the
[tree_db](@yw-nav-mod:backends.tree_db) service.

The endpoints described here mostly:
*  check authorization
*  forward to the underlying service by adjusting the URL.
*  in case of assets creation or deletion, orchestrate the different required steps.

Please refer to the documentation of the underlying service for detailed description of parameters and returned
response.
"""
