"""
This module defines the [HTTP API router](https://fastapi.tiangolo.com/reference/apirouter/?h=apir) responsible
for custom backend-related features. The router is accessible from the base URL:

> **`/backends`**

# Introduction

In this page, **backends** refer to HTTP services that can be installed and served on demand.
These backends can be requested by applications using `webpm`, for example:

<code-snippet language="javascript">
const fooClient = webpm.install({backends:['foo#^1.0.0 as fooClient']})
await fooClient.fetch(url, options)
// also fetchJson, fetchText, ... See WebPM documentation.
</code-snippet>

Here, `webpm` is the installer client. For more information, see the
<a target="_blank" href="/applications/@youwol/webpm-client-doc/latest?nav=/">WebPM's Client Documentation</a>.

<note level="hint">
You can pass custom build arguments to `webpm.install` that are forwarded to the backend installation process.
</note>

Once a backend is installed, any HTTP requests to:

`/backends/{NAME}/{SEMVER}/rest/of/path`

are redirected appropriately to the targeted backend. See the discussion about partitions below.

<expandable title="Details" icon="fas fa-question-circle text-success">

When `webpm.install` is called, the WebPM client performs the following steps:
*  1. Calls the endpoint :func:`youwol.backends.cdn.root_paths.resolve_loading_tree` to resolve the dependency tree.
*  2. Calls the endpoint :func:`youwol.app.routers.system.router.install_graph` to install and start the required
backends.

Once a backend is installed, requests are redirected by the functions:
*  :func:`youwol.app.routers.backends.router.dispatch_get`,
*  :func:`youwol.app.routers.backends.router.dispatch_post`,
*  :func:`youwol.app.routers.backends.router.dispatch_put` and
*  :func:`youwol.app.routers.backends.router.dispatch_delete`, all of them based on the common

All of these dispatch methods rely on the common function :func:`youwol.app.routers.backends.router.dispatch_impl`
function.


<note level="hint">
If you send an HTTP request to `/backends/{NAME}/{SEMVER}/rest/of/path` without explicitly installing the backend first,
the system will install and start the backend on demand.
However, any direct or indirect dependencies will **not** be installed unless you explicitly call `webpm.install`.
Explicit installation also enables you to manage deployment within a specific partition, as described below, as well
as provide specific build arguments.
</note>

</expandable>


#  Backend Deployment

Depending on how the backend is packaged, YouWol supports two deployment options.

## Container-Based Deployment

If a `Dockerfile` is provided in the root folder of the backend, the deployment will be containerized.
This method ensures precise, reproducible control over the backend’s environment.

When installation is requested and no corresponding Docker image exists, an image is built using optional build
arguments passed through `webpm.install`. The service is then started by creating a container from the built image.


If the author provided a `Dockerfile` within the root folder of the backend, the deployment is achieved within
a container. This is the preferred option as it allows to have a precise - and reproducible- control over the
environment in which the backend is started.

When installation is requested - if no corresponding image already exists-,
an image is build - including optional build arguments provided with the call from `webpm.install`.
Starting the service is then achieved by creating a container given the built image.

## Localhost-Based Deployment

In this option, the backend provides two scripts, `install.sh` and `start.sh`.
These scripts handle installation and startup on the local machine.

<note level="warning">
This method is less recommended due to the potential complexity of cross-platform shell scripts.
These scripts often assume the presence of software that may not exist or may be installed in incompatible versions.
</note>

When installation is requested and no build manifest is available, the `install.sh` script is executed,
often creating a sandboxed environment and installing dependencies.
The `start.sh` script is then run to serve the backend.

# Partitioning

Partitioning refers to the creation of isolated clusters of backend instances. Backends within a partition can only
communicate with other backends in the same partition, ensuring separation and isolation.

Typically, a partition is defined by the application requesting the installation of backends.
This approach ensures that the backend instances are dedicated to a specific application, preventing any mixing of
backend states or configurations across multiple applications.

In this way, partitioning helps maintain clean and independent execution environments, ensuring that backend services
remain isolated from one another unless explicitly designed to interact within the same partition.

Partitioning occurs at two stages:
*  **At installation**: During `wepm.install`, you can specify a `partition` in the `backends`specification.
. If no ID is provided, the partition defaults to the application name.
*  **At runtime**: When the application sends requests, it includes a header
:attr:`youwol.utils.utils.YouwolHeaders.backends_partition` which directs requests to the correct partition.
"""

# relative
from .router import *
