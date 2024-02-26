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
from youwol.app.environment.models.models import (
    ConfigPath,
    OnProjectsCountUpdate,
    ProjectsFinderHandler,
)
from youwol.app.environment.models.projects_finder_handlers import (
    ExplicitProjectsFinderHandler,
    RecursiveProjectFinderHandler,
)
from youwol.app.environment.paths import PathsBook

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
    Abstract class for ProjectsFinder.

    Derived classes need to implement the **'handler'** method.

    See [RecursiveProjectsFinder](@yw-nav-class:RecursiveProjectsFinder) and
    [ExplicitProjectsFinder](@yw-nav-class:ExplicitProjectsFinder).
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ) -> ProjectsFinderHandler:
        raise NotImplementedError()


class RecursiveProjectsFinder(ProjectsFinder):
    """
    Strategy to discover all projects below the provided paths with optional continuous watching.

    Example:
        <code-snippet language="python" highlightedLines="6 13-17">
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                RecursiveProjectsFinder
            )

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=RecursiveProjectsFinder(
                    fromPaths=[projects_folder],
                    ignoredPatterns=["**/dist", "**/node_modules", "**/.template"],
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

    fromPaths: list[ConfigPath] = [Path.home() / default_path_projects_dir]
    """
    All projects below these paths will be discovered.

    By default uses
    [default_path_projects_dir](@yw-nav-glob:default_path_projects_dir).
    """

    ignoredPatterns: list[str] = default_ignored_paths
    """
    List of ignored patterns to discard folder when traversing the tree.

    By default uses [default_ignored_paths](@yw-nav-glob:default_ignored_paths).

    See [fnmatch](https://docs.python.org/3/library/fnmatch.html) regarding the patterns specification.
    """
    watch: bool = True
    """
    Whether or not watching added/removed projects is activated.
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ):
        return RecursiveProjectFinderHandler(
            paths=self.fromPaths,
            ignored_patterns=self.ignoredPatterns,
            paths_book=paths_book,
            on_projects_count_update=on_projects_count_update,
        )


class ExplicitProjectsFinder(ProjectsFinder):
    """
    Strategy to discover all projects directly below some provided paths.

     > ⚠️ Changes in directories content is not watched: projects added/removed from provided paths do not trigger
     updates.
     The [RecursiveProjectsFinder](@yw-nav-class:RecursiveProjectsFinder)
     class allows such features.

     Example:
        <code-snippet language="python" highlightedLines="6 13-15">
        from pathlib import Path

        from youwol.app.environment import (
                Configuration,
                Projects,
                ExplicitProjectsFinder
            )

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=ExplicitProjectsFinder(
                    fromPaths=[projects_folder]
                )
            )
        )
        </code-snippet>

    """

    fromPaths: list[ConfigPath] | Callable[[PathsBook], list[ConfigPath]]
    """
    The paths in which to look for projects as direct children.

    Can be provided as a function that gets the [PathsBook](@yw-nav-class:PathsBook)
    instance - useful when looking for folder's location depending on some typical paths of youwol.
    """

    def handler(
        self, paths_book: PathsBook, on_projects_count_update: OnProjectsCountUpdate
    ):
        return ExplicitProjectsFinderHandler(
            paths=self.fromPaths,
            paths_book=paths_book,
            on_projects_count_update=on_projects_count_update,
        )


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
                RecursiveProjectsFinder
            )
        from youwol.pipelines.pipeline_typescript_weback_npm import app_ts_webpack_template

        projects_folder = Path.home() / 'Projects'

        Configuration(
            projects=Projects(
                finder=RecursiveProjectsFinder(
                    fromPaths=[projects_folder],
                ),
                templates=[app_ts_webpack_template(folder=projects_folder)],
            )
        )
        </code-snippet>
    """

    finder: ProjectsFinder | ConfigPath = RecursiveProjectsFinder()
    """
    Strategy for finding projects, most of the times the
    [RecursiveProjectsFinder](@yw-nav-class:RecursiveProjectsFinder)
    strategy is employed.
    The less employed
    [ExplicitProjectsFinder](@yw-nav-class:ExplicitProjectsFinder)
    can also be used.
    """

    templates: list[ProjectTemplate] = []
    """
    List of projects' template: they are essentially generators that create an initial project structure for a
     particular stack.
    """
