"""
This module gathers the multiple
:class:`youwol.app.middlewares.local_cloud_hybridizers.abstract_local_cloud_dispatch.AbstractLocalCloudDispatch`
used in
:class:`youwol.app.middlewares.hybridizer_middleware.LocalCloudHybridizerMiddleware`
to accomplish actions (e.g. downloads, queries) requiring
HTTP calls to the
:attr:`youwol.app.environment.youwol_environment.YouwolEnvironment.currentConnection` (the remote ecosystem).

"""

# relative
from .abstract_local_cloud_dispatch import *
from .custom_backends import *
from .deprecated_rules import *
from .download_rules import *
from .forward_only_rules import *
from .loading_graph_rules import *
from .workspace_explorer_rules import *
