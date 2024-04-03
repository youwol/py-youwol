# future
from __future__ import annotations

# standard library
import asyncio
import dataclasses
import os
import time

from collections.abc import Callable, Coroutine
from fnmatch import fnmatch
from pathlib import Path
from threading import Thread

# typing
from typing import Any

# third parties
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

# Youwol
from youwol import app

# Youwol application
from youwol.app.environment import ProjectsFinder
from youwol.app.environment.paths import PathsBook

# Youwol utilities
from youwol.utils import log_info

OnProjectsCountUpdate = Callable[
    [tuple[str, list[Path], list[Path]]], Coroutine[None, Any, None]
]
"""
Defines a callback type that is invoked when there is an update in the count of projects, specifically when projects
are added or removed.

It takes as arguments a tuple containing:
1.  A string indicating the name of the [ProjectsFinder](@yw-nav-class:models_project.ProjectsFinder)
that discovered the updates.
2.  A list of Path objects representing the projects that were added.
3.  A list of Path objects representing the projects that were removed.

It returns an awaitable object that, when awaited, completes with None. This allows for asynchronous processing
within the callback.
"""


def auto_detect_projects(
    root_folder: Path | str,
    ignore: list[str] | None = None,
    max_depth: int | None = None,
) -> list[Path]:
    """
    Automatically detects projects within a specified root folder, excluding specified paths and system directories.

    This function traverses the directory tree starting from `root_folder`, looking for directories that contain
    a `.yw_pipeline/yw_pipeline.py` file, which indicates a YouWol pipeline project. It excludes directories
    specified by the `ignore` parameter.

    Warning:
        Folders whose names begin with a `.` are excluded from the search process.

    Parameters:
        root_folder: The root directory from which the search should start.
        ignore: A list of glob patterns to ignore during the search.
            When traversing the folder tree, a folder (and its descendants) will be discarded if
            `fnmatch(relative_folder_path, pattern)`  returns `True` for one of the pattern.
        max_depth: The maximum depth of recursion during the directory search. If None, the search
            will explore directories recursively without limit. Defaults to None.

    Return:
        A list of `Path` objects, each representing a project directory (containing a
        `.yw_pipeline/yw_pipeline.py` file).
         If no projects are found, or if `root_folder` does not exist, an empty list is returned.
    """
    root_folder = Path(root_folder)
    if not root_folder.exists():
        return []

    return directories_finder(
        folder=root_folder,
        ignore=ignore or [],
        condition=lambda path: (path / ".yw_pipeline" / "yw_pipeline.py").exists(),
        max_depth=max_depth,
    )


def directories_finder(
    folder: Path | str,
    condition: Callable[[Path], bool],
    ignore: list[str] | None = None,
    max_depth: int | None = None,
) -> list[Path]:
    """
    Searches recursively through a directory tree, starting from a given folder, and selects directories that
    satisfy a specified condition, while optionally ignoring certain paths and adhering to a maximum search depth.

    Warning:
        Folders whose names begin with a `.` are excluded from the search process.


    Parameters:
        folder: The root directory from which to start the search.
        condition: A function that takes a `Path` object as input and returns `True` if the
            directory meets the criteria for selection, and `False` otherwise.
        ignore: A list of glob patterns to ignore during the search.
            When traversing the folder tree, a folder (and its descendants) will be discarded if
            `fnmatch(relative_folder_path, pattern)`  returns `True` for one of the pattern.
        max_depth: The maximum depth of subdirectories to traverse. A value of None indicates no limit
            on the depth of the search. The depth is calculated relative to the `folder`.

    Return:
        A list of Path objects, each representing a directory that satisfies the condition.
    """

    folder = Path(folder)
    ignore = ignore or []
    selected: list[Path] = []
    for root, dirs, _ in os.walk(folder):
        current_depth = len(Path(root).relative_to(folder).parts)
        if max_depth and current_depth > max_depth:
            dirs.clear()
            continue
        root_path = Path(root)
        if root_path.name.startswith("."):
            dirs.clear()
            continue
        relative_root_path = root_path.relative_to(folder)
        if any(fnmatch(str(relative_root_path), pattern) for pattern in ignore):
            dirs.clear()
            continue
        if condition(root_path):
            selected.append(root_path)

    return selected


class ProjectsWatcherEventsHandler(PatternMatchingEventHandler):
    """
    An event handler designed for watching project directories and triggering actions on project creation and deletion.

    Projects are identified by the presence of a `.yw_pipeline/yw_pipeline.py` file;
    it notifies an [owner](@yw-nav-class:ProjectsFinderImpl) object about changes in the projects' count.
    """

    def __init__(
        self, owner: ProjectsFinderImpl, ignored_patterns: list[str], from_path: Path
    ):
        """
        Initialize a new instance.

        Parameters:
            owner: The owner instance responsible for handling updates on project counts.
            ignored_patterns: A list of glob patterns to ignore regarding folders.
                Folders matching these patterns will not trigger events.
            from_path: The path from which projects' path are expressed.
                E.g., if referencing a symbolic link, notification to the [owner](@yw-nav-class:ProjectsFinderImpl)
                are expressed with it (and not from its absolute counterpart).

        Parameters are set as class attributes.
        """
        super().__init__(ignore_patterns=ignored_patterns)
        self.owner = owner
        self.from_path = from_path
        self.from_path_absolute = self.from_path.resolve()

    def on_created(self, event: FileSystemEvent):
        """
        Handles project creation events. It determines if the created file is a `yw_pipeline.py` within a
        `.yw_pipeline` directory, indicating a project creation, and notifies the owner.

        Parameters:
            event: source event
        """
        super().on_created(event)
        project_path = self.project_path(event)
        if project_path:
            log_info(f"ProjectsWatcherEventsHandler: project created: {project_path}")
            asyncio.run(self.owner.trigger_update(([project_path], [])))

    def on_deleted(self, event):
        """
        Similar to `on_created` but handles project deletion events.

        Parameters:
            event: source event
        """
        super().on_deleted(event)
        project_path = self.project_path(event)
        if project_path:
            log_info(f"ProjectsWatcherEventsHandler project deleted: {project_path}")
            asyncio.run(self.owner.trigger_update(([], [project_path])))

    def project_path(self, event: FileSystemEvent) -> Path | None:
        """
        A utility method to extract the project path from the event's source path if the event represents
        a project creation or deletion. Returned paths are expressed using the `from_path` attribute provided at
        initialization (which can involved symbolic link).

        Parameters:
            event: source event

        Return:
            A `Path` if the event is associated to a project creation, `None` otherwise.
        """
        path = Path(event.src_path)
        if path.name == "yw_pipeline.py" and path.parent.name == ".yw_pipeline":
            project_absolute_path = path.parent.parent
            return self.from_path / project_absolute_path.relative_to(
                self.from_path_absolute
            )

        return None


class ProjectsWatcher(Thread):
    """
    A thread that monitors a directory tree for changes indicating the creation or deletion of projects.

    This class extends `Thread` to continuously watch a specified path for file system events that suggest a
     project has been created or deleted.
     It uses an instance of [ProjectsWatcherEventsHandler](@yw-nav-class:ProjectsWatcherEventsHandler) to handle these
     events and notify an [owner}(@yw-nav-class:ProjectsFinderImpl) of the changes.
    """

    def __init__(
        self, owner: ProjectsFinderImpl, from_path: Path, ignored_patterns: list[str]
    ):
        """
        Initialize a new instance.

        Parameters:
            owner: The owner instance responsible for handling updates on project counts.
            from_path: The root path from which to start monitoring for project-related changes.
            ignored_patterns: A list of glob patterns to ignore regarding folders.
                Folders matching these patterns will not trigger events.

        Parameters are set as class attributes.
        """
        super().__init__()
        self.owner = owner
        self.from_path = from_path
        self.ignored_patterns = ignored_patterns
        self.stopped = False
        self.event_handler = None

    def go(self):
        """
        Starts the watcher thread.
        """
        self.start()

    def stop(self):
        """
        Signals the watcher thread to stop.
        """
        self.stopped = True

    def run(self) -> None:
        """
        The entry point for the thread's execution, setting up the observer and event handler,
        and starting the monitoring process.
        """
        observer = Observer()
        self.event_handler = ProjectsWatcherEventsHandler(
            owner=self.owner,
            ignored_patterns=self.ignored_patterns,
            from_path=self.from_path,
        )
        observer.schedule(self.event_handler, str(self.from_path), recursive=True)
        observer.start()

        log_info(
            f"Look-up thread started for projects-finder '{self.owner.name}' (from folder '{self.from_path}')"
        )
        while not self.stopped:
            time.sleep(1)
        log_info(
            f"Look-up thread stopped for projects-finder '{self.owner.name}' (from folder '{self.from_path}')"
        )
        observer.stop()
        observer.join()


@dataclasses.dataclass
class ProjectsFinderImpl:
    """
    Implementation of a [project finder](@yw-nav-class:models_project.ProjectsFinder) that scans a specified directory
    path for projects, with options for depth control, ignoring certain paths, and dynamically watching for changes.

    It uses a combination of directory scanning and filesystem event monitoring to maintain an up-to-date view of
    projects within a specified path.

    Warning:
        Folders whose names begin with a `.` are excluded from the search process.
    """

    name: str
    """
    Reference name.
    """

    from_path: Path
    """
    The root path from which the project search begins.
    """
    look_up_depth: int
    """
    The maximum depth relative to `from_path` to search for projects. A depth of 0 means only the root path
    is considered.
    """
    look_up_ignore: list[str]
    """
    Paths to ignore during the search, specified as strings that can match relative path of directories
    during the search process.
    """
    watch: bool
    """
    Whether to dynamically watch the `from_path` for changes and update the project list accordingly.
    """
    paths_book: PathsBook
    """
    An object containing various predefined paths, used to auto-configure additional ignore patterns.
    """
    on_projects_count_update: OnProjectsCountUpdate
    """
    A callback function to be invoked when the list of projects is updated (projects are added or removed).
    """
    watcher: ProjectsWatcher | None = None
    """
    An optional background thread that monitors filesystem events for dynamic updates if `watch` is True.
    """

    def __post_init__(self):

        database_ignore = None
        system_ignore = None
        pipelines_ignore = None
        try:
            database_ignore = self.paths_book.databases.relative_to(self.from_path)
        except ValueError:
            pass
        try:
            system_ignore = self.paths_book.system.relative_to(self.from_path)
        except ValueError:
            pass
        try:
            pipelines_path = app.__file__
            if pipelines_path is not None:
                pipelines_ignore = Path(pipelines_path).parent.relative_to(
                    self.from_path
                )
        except ValueError:
            pass
        native_ignores = [database_ignore, system_ignore, pipelines_ignore]
        ignore = (self.look_up_ignore or []) + [
            str(path) for path in native_ignores if path
        ]
        self.look_up_ignore = ignore

    async def initialize(self):
        """
        Prepares the finder by performing an initial scan and setting up the watcher if required.
        """
        await self.explicit_refresh()
        if not self.watch:
            return
        self.release()
        self.watcher = ProjectsWatcher(
            owner=self, from_path=self.from_path, ignored_patterns=self.look_up_ignore
        )
        self.watcher.go()

    async def explicit_refresh(self):
        """
        Forces a re-scan of the `from_path` to update the list of projects.
        """
        if self.look_up_depth == 0:
            await self.trigger_update(([self.from_path], []))
            return
        project_paths = auto_detect_projects(
            root_folder=self.from_path,
            ignore=self.look_up_ignore,
            max_depth=self.look_up_depth,
        )
        await self.trigger_update((project_paths, []))

    async def refresh(self):
        """
        Refreshes the project list: it triggers an explicit refresh.
        """
        await self.explicit_refresh()
        # if self.watch =>  any created/removed projects should be caught by `self.watcher`.

    def release(self):
        """
        Stops and releases the watcher thread if it's running.
        """
        if self.watcher:
            self.watcher.stop()
            self.watcher.join()

    async def trigger_update(self, update: tuple[list[Path], list[Path]]):
        """
        Processes an update to the list of projects, distinguishing between added and removed projects,
        and calls the `on_projects_count_update` callback with the update details.

        Parameters:
            update: Update details.
        """
        added = [
            p
            for p in update[0]
            if len(p.relative_to(self.from_path).parts) <= self.look_up_depth
        ]
        removed = [
            p
            for p in update[1]
            if len(p.relative_to(self.from_path).parts) <= self.look_up_depth
        ]
        await self.on_projects_count_update((self.name, added, removed))


class GlobalProjectsFinder:
    """
    Manages multiple [project finder instances](@yw-nav-class:ProjectsFinderImpl) to collectively scan and
    monitor projects across different paths.
    """

    def __init__(
        self,
        finders: list[ProjectsFinder],
        paths_book: PathsBook,
        on_projects_count_update: OnProjectsCountUpdate,
    ):
        self.handlers = [
            ProjectsFinderImpl(
                name=f.name,
                from_path=Path(f.fromPath),
                look_up_ignore=f.lookUpIgnore,
                look_up_depth=f.lookUpDepth,
                watch=f.watch,
                paths_book=paths_book,
                on_projects_count_update=on_projects_count_update,
            )
            for f in finders
        ]

    async def initialize(self):
        """
        Initializes all project finder instances, triggering their respective scanning and monitoring processes.
        """
        await asyncio.gather(*[handler.initialize() for handler in self.handlers])

    async def refresh(self):
        """
        Refreshes all project finder instances, updating the project lists based on the current state of the filesystem.
        """
        await asyncio.gather(*[handler.refresh() for handler in self.handlers])

    def release(self):
        """
        Releases all resources associated with the project finder instances, stopping any active monitoring processes.
        """
        for handler in self.handlers:
            handler.release()
