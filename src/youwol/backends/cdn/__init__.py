"""
This module gathers the service `cdn-backend`.

Responsibilities:
    *  resolve dependencies tree when requesting dependencies installation
    *  serve the resources (e.g. javascript files, css, *etc.*) like a regular CDN


Accessibility:
    *  It is served from the path `/api/cdn-backend`.
    *  In its remote version, it is accessible only via the
        [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/cdn-backend`.

Dependencies:
    *  a [filesystem service](@yw-nav-attr:youwol.backends.cdn.configurations.Configuration.file_system),
    using a bucket defined by this [namespace](@yw-nav-attr:youwol.backends.cdn.configurations.Constants.namespace)
    *  a [no-sql service](@yw-nav-attr:youwol.backends.cdn.configurations.Configuration.doc_db),
     with a single table in this [namespace](@yw-nav-attr:youwol.backends.cdn.configurations.Constants.namespace)
      defined by [schema_docdb](@yw-nav-attr:youwol.backends.cdn.configurations.Constants.schema_docdb).
"""
# relative
from .configurations import Configuration, Constants, Dependencies
from .resources_initialization import init_resources
from .root_paths import *
from .router import get_router
