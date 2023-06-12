# standard library
import asyncio
import fnmatch
import itertools
import time
import traceback

from pathlib import Path
from threading import Thread

# typing
from typing import Callable, List, Optional, Union

# third parties
from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

# Youwol application
from youwol.app.environment.models.models import (
    ConfigPath,
    OnProjectsCountUpdate,
    ProjectsFinderHandler,
)
from youwol.app.environment.paths import PathsBook
from youwol.app.environment.projects_finders import auto_detect_projects
from youwol.app.web_socket import WsDataStreamer

# Youwol utilities
from youwol.utils import Context, log_info


class ExplicitProjectsFinderHandler(ProjectsFinderHandler):
    paths: Union[List[ConfigPath], Callable[[PathsBook], List[ConfigPath]]]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate

    def __init__(
        self,
        paths: Union[List[ConfigPath], Callable[[], List[ConfigPath]]],
        paths_book: PathsBook,
        on_projects_count_update: OnProjectsCountUpdate,
    ):
        self.paths = paths
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update

    async def initialize(self):
        project_paths = (
            self.paths(self.paths_book) if callable(self.paths) else self.paths
        )
        await self.on_projects_count_update((project_paths, []))

    async def refresh(self):
        await self.initialize()


class RecursiveFinderEventHandler(FileSystemEventHandler):
    context: Context
    paths: List[Path]
    ignored_patterns: List[str]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate

    def __init__(
        self,
        paths: List[Path],
        ignored_patterns: List[str],
        paths_book: PathsBook,
        on_projects_count_update: OnProjectsCountUpdate,
        context: Context,
    ):
        super().__init__()
        self.paths = paths
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update
        self.ignored_patterns = (
            ignored_patterns
            + [f"{p}/**" for p in ignored_patterns]
            + [f"{paths_book.system}/**", f"{paths_book.databases}/**"]
        )
        self.context = context
        asyncio.run(self.reload())

    async def reload(self):
        results = [
            auto_detect_projects(
                paths_book=self.paths_book,
                root_folder=root_folder,
                ignore=self.ignored_patterns,
            )
            for root_folder in self.paths
        ]

        results = list(itertools.chain.from_iterable(results))
        log_info(f"Found {len(results)} projects")

        await self.on_projects_count_update((results, []))

    def on_created(self, event: FileSystemEvent):
        super().on_created(event)
        project_path = self.project_path(event)
        if project_path:
            asyncio.run(self.on_projects_count_update(([project_path], [])))

    def on_deleted(self, event):
        super().on_deleted(event)
        project_path = self.project_path(event)
        if project_path:
            asyncio.run(self.on_projects_count_update(([], [project_path])))

    def project_path(self, event: FileSystemEvent) -> Optional[Path]:
        if not any(
            isinstance(event, Type) for Type in [DirCreatedEvent, DirDeletedEvent]
        ):
            return None
        path = event.src_path

        if Path(path).name != ".yw_pipeline":
            return None
        # we should also ignore the PathBook.database and PathBook.system
        # make Projects.finder.ignoredPattern a function
        ignored = any(
            fnmatch.fnmatch(path, pattern) for pattern in self.ignored_patterns
        )
        if ignored:
            return None

        return Path(path).parent


class RecursiveProjectsFinderThread(Thread):
    paths: List[Path]
    ignored_patterns: List[str]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate

    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    event_handler: RecursiveFinderEventHandler

    stopped = False

    def __init__(
        self,
        paths: List[Path],
        ignored_patterns: List[str],
        paths_book: PathsBook,
        on_projects_count_update: OnProjectsCountUpdate,
    ):
        super().__init__()
        self.paths = paths
        self.ignored_patterns = ignored_patterns
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update

    def go(self):
        self.start()

    def stop(self):
        self.stopped = True

    def run(self) -> None:
        observer = Observer()
        self.event_handler = RecursiveFinderEventHandler(
            paths=self.paths,
            ignored_patterns=self.ignored_patterns,
            paths_book=self.paths_book,
            on_projects_count_update=self.on_projects_count_update,
            context=self.context,
        )

        for folder in self.paths:
            if not Path(folder).exists():
                continue
            observer.schedule(self.event_handler, str(folder), recursive=True)

        observer.start()

        log_info(
            f"RecursiveProjectsFinderThread started, folders: {[f'{p}' for p in self.paths]}"
        )
        while not self.stopped:
            time.sleep(1)
        observer.stop()
        observer.join()


class RecursiveProjectFinderHandler(ProjectsFinderHandler):
    paths: List[Path]
    ignored_patterns = List[str]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate
    thread: Optional[RecursiveProjectsFinderThread]

    def __init__(
        self,
        paths: List[Path],
        ignored_patterns: List[str],
        paths_book: PathsBook,
        on_projects_count_update: OnProjectsCountUpdate,
    ):
        self.paths = paths
        self.ignored_patterns = ignored_patterns
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update
        self.thread = None

    async def initialize(self):
        self.release()
        self.thread = RecursiveProjectsFinderThread(
            paths=self.paths,
            ignored_patterns=self.ignored_patterns,
            paths_book=self.paths_book,
            on_projects_count_update=self.on_projects_count_update,
        )
        try:
            self.thread.go()
        except RuntimeError as e:
            print("Error while starting projects RecursiveProjectsFinderThread")
            traceback.print_exception(type(e), value=e, tb=e.__traceback__)
            raise e

    async def refresh(self):
        # There is no reasons to do anything here: any created/removed projects should have already been caught.
        pass

    def release(self):
        if self.thread:
            self.thread.stop()
            self.thread.join()
