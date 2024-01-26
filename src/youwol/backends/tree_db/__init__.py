"""
This module gathers the service `treedb-backend`.

Responsibilities:
    *  manage the file system like organisation of assets.

    The leaf of the 'files' tree structure are called **item**, the node are called **folder**.
    All folders and items belong to a **drive**, they are themselves children of a **group**.

    To explorer the items of a user, request to the users' group need to be achieved first, then the groups' drives,
    then recursively the folders (see
    [get_groups](@yw-nav-class:youwol.backends.tree_db.root_paths.get_groups),
    [list_drives](@yw-nav-class:youwol.backends.tree_db.root_paths.list_drives),
    [children](@yw-nav-class:youwol.backends.tree_db.root_paths.children)).

    Among the drives of a group, one is called the **Default drive**, it is associated to some predefined folders
    (see [get_default_drive](@yw-nav-class:youwol.backends.tree_db.root_paths.get_default_drive), or
     [get_default_user_drive](@yw-nav-class:youwol.backends.tree_db.root_paths.get_default_user_drive)).

Accessibility:
    *  It is served from the path `/api/treedb-backend`.
    *  In its remote version, it is accessible only via the
        [assets_gateway](@yw-nav-mod:youwol.backends.assets_gateway) service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/treedb-backend`.

Dependencies:
    *  Dependencies are gathered in the
    [Configuration](@yw-nav-class:youwol.backends.tree_db.configurations.Configuration) class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import *
from .router import get_router
