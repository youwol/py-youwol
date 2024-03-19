"""
This file gathers [project](@yw-nav-class:models_project.Project) related models of the
[configuration](@yw-nav-class:models_config.Configuration).
"""

# standard library
from collections.abc import Awaitable, Callable
from pathlib import Path

# typing
from typing import Any

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment.models.defaults import (
    default_ignored_paths,
    default_path_projects_dir,
)
from youwol.app.environment.models.models import ConfigPath

# Youwol utilities
from youwol.utils import Context


class ProjectTemplate(BaseModel):
    """
    Definition of a template that create an initial project folder that can be built & published.

    In most practical cases, project template generator are exposed by python packages and consumed in the configuration
    file, for instance regarding the typescript pipeline of youwol:

    <code-snippet language="python" highlightedLines="5 11">
    from youwol.app.environment import (
        Configuration,
        Projects,
    )
    from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

    projects_folder = Path.home() / 'destination'

    Configuration(
        projects=Projects(
            templates=[app_ts_webpack_template(folder=projects_folder)],
        )
    )
    </code-snippet>

    """

    icon: Any
    """
    A json DOM representation of the icon for the template. See the library '@youwol/rx-vdom'.
    """

    type: str
    """
    A unique type id that represents the type of the project.
    """

    folder: str | Path
    """
    Where the created project folders will be located.
    """

    parameters: dict[str, str]
    """
    A dictionary *'parameter name'* -> *'parameter default value'* defining the parameters the user will have to supply
    to create the template.
    """

    generator: Callable[[Path, dict[str, str], Context], Awaitable[tuple[str, Path]]]
    """
    The generator called to create the template project, arguments are:

    1 - First argument is the folder's path in which the project needs to be created (parent folder
        of the created project).

    2 - Second argument is the value of the parameters the user supplied.

    3 - Third argument is the context.

    Return the project's name and its path.
    """


class ProjectsFinder(BaseModel):
    """
    Strategy to discover projects below a provided folder on the user's hard drive with optional continuous watching.

    Warning:
        Folders whose names begin with a `.` are excluded from the search process.

    Example:
        <code-snippet language="python" highlightedLines="6 13-17">
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                ProjectsFinder
            )

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=ProjectsFinder(
                    fromPaths=Path.home() / 'Projects',
                    lookUpDepth=2
                    lookUpIgnore=["**/dist", "**/node_modules", "**/.template"],
                    watch=True
                )
            )
        )
        </code-snippet>

    **Troubleshooting**

    Inotify uses a system-wide limit called `max_user_watches`, which determines the maximum number of files or
    directories that a user can watch at any given time. This limit is set by the system administrator
    and is typically set to a low value such as `8192` or `16384`.
    When the limit is reached, inotify will stop working and will not be able to watch for changes
    in any additional files or directories. A common displayed error in such case is:
    ```bash
    Failed to watch /var/log/messages; upper limit on inotify watches reached!
    Please increase the amount of inotify watches allowed per user via '/proc/sys/fs/inotify/max_user_watches'.`
    ```

    To increase the limit, you can edit the `sysctl.conf` file and add a line to increase the `max_user_watches` limit.
    For example:
    ```bash
    echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
    ```
    Then run

    ```bash
    sudo sysctl -p
    ```
    This will increase the max_user_watches limit to the new value.

    Note that this change will not take effect until the system is rebooted.
    You may also check the current value of the limit by running

    ```bash
    cat /proc/sys/fs/inotify/max_user_watches
    ```

    The value `524288` is a commonly used value for increasing the max_user_watches limit because it's a reasonably
     large number that should be sufficient for most use cases.
    It allows a user to watch up to `524288` files or directories at any given time.
    This value is typically high enough to handle most use cases and should be enough to prevent inotify from
    reaching its limit and stop working.
    """

    name: str | None = None
    """
    Reference name, if not provided the name of the associated `fromPath` folder is used.
    """

    fromPath: ConfigPath = Path.home() / default_path_projects_dir
    """
    All projects below these paths will be discovered.

    By default uses
    [default_path_projects_dir](@yw-nav-glob:default_path_projects_dir).
    """

    lookUpDepth: int = 3
    """
    Maximum recursion depth from starting folder.
    """

    lookUpIgnore: list[str] = default_ignored_paths
    """
    List of ignored patterns to discard folder when traversing the tree.

    By default uses [default_ignored_paths](@yw-nav-glob:default_ignored_paths).

    See [fnmatch](https://docs.python.org/3/library/fnmatch.html) regarding the patterns specification.
    """
    watch: bool = False
    """
    If `True`, continuously watch for projects creation/deletion.
    """

    def __init__(self, **data):
        super().__init__(**data)
        self.name = self.name or Path(self.fromPath).name


ConfigProjectsFinder = ProjectsFinder | ConfigPath
"""
Permissive type to define [Projects.finder](@yw-nav-attr:Projects.finder).
"""


class Projects(BaseModel):
    """
    It essentially defines the projects a user is working on, including:

    *  a strategy to locate them from the local disk.
    *  some references on `template` objects that allows to create an initial draft of a project for a particular stack

    Example:
        A typical example of this section of the configuration looks like:

        <code-snippet language="python" highlightedLines="5 6 8 13 14 15 16 17 18">
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                ProjectsFinder
            )
        from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=ProjectsFinder(
                    fromPath=projects_folder,
                ),
                templates=[app_ts_webpack_template(folder=projects_folder)],
            )
        )
        </code-snippet>
    """

    finder: list[ConfigProjectsFinder] | ConfigProjectsFinder = ProjectsFinder()
    """
    One or more [ProjectsFinder](@yw-nav-class:ProjectsFinder).

    When a `ConfigPath` is provided as `ConfigProjectsFinder`, a default `ProjectsFinder` instance is created with
    its `fromPath` attribute set to the provided value.
    """

    templates: list[ProjectTemplate] = []
    """
    List of projects' template: they are essentially generators that create an initial project structure for a
     particular stack.
    """
