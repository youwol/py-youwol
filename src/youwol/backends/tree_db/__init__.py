"""
This module gathers the service `treedb-backend`.

Responsibilities:
    *  manage the file system like organisation of assets.

    The leaf of the 'files' tree structure are called **item**, the node are called **folder**.
    All folders and items belong to a **drive**, they are themselves children of a **group**.

    To explorer the items of a user, request to the users' group need to be achieved first, then the groups' drives,
    then recursively the folders (see
    :func:`get_groups <youwol.backends.tree_db.routers.groups.get_groups>`,
    :func:`list_drives <youwol.backends.tree_db.routers.groups.list_drives>`,
    :func:`children <youwol.backends.tree_db.routers.folders.children>`).

    Among the drives of a group, one is called the **Default drive**, it is associated to some predefined folders
    (see :func:`get_default_drive <youwol.backends.tree_db.routers.groups.get_group_default_drive>`, or
     :func:`get_default_user_drive <youwol.backends.tree_db.routers.drives.get_default_user_drive>`).

Accessibility:
    *  It is served from the path `/api/treedb-backend`.
    *  In its remote version, it is accessible only via the
        :mod:`assets_gateway <youwol.backends.assets_gateway>` service (to allow permissions validation).
        In this case, it is served from the path `/api/assets-gateway/treedb-backend`.

Dependencies:
    *  Dependencies are gathered in the
    :class:`Configuration <youwol.backends.tree_db.configurations.Configuration>` class.
"""

# relative
from .configurations import Configuration, Constants, Dependencies
from .router import get_router
