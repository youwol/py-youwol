"""
This module gathers the multiple
<a href="@yw-nav-class:youwol.app.middlewares.local_cloud_hybridizers.abstract_local_cloud_dispatch.
AbstractLocalCloudDispatch">AbstractLocalCloudDispatch</a>
used in
<a href="@yw-nav-class:youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware">
LocalCloudHybridizerMiddleware</a>
to accomplish actions (e.g. downloads, queries) requiring
HTTP calls to the
<a href="@yw-nav-attr:youwol.app.environment.youwol_environment.YouwolEnvironment.currentConnection">
YouwolEnvironment.currentConnection</a> (to the remote ecosystem).

"""

# relative
from .abstract_local_cloud_dispatch import *
from .deprecated_rules import *
from .download_rules import *
from .forward_only_rules import *
from .loading_graph_rules import *
from .workspace_explorer_rules import *
