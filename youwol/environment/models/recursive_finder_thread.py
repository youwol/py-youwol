import asyncio
import fnmatch
import itertools
import time
from pathlib import Path
from threading import Thread
from typing import List, Callable, Tuple, Optional, Awaitable

from watchdog.events import FileSystemEventHandler, FileSystemEvent, DirCreatedEvent, DirDeletedEvent
from watchdog.observers import Observer

from youwol.environment.projects_finders import auto_detect_projects
from youwol.environment.paths import PathsBook
from youwol.web_socket import WsDataStreamer
from youwol_utils import Context, log_info

OnProjectsCountUpdate = Callable[[Tuple[List[Path], List[Path]]], Awaitable[None]]


class RecursiveFinderEventHandler(FileSystemEventHandler):

    context: Context
    paths: List[Path]
    ignored_patterns: List[str]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate

    def __init__(self,
                 paths: List[Path],
                 ignored_patterns: List[str],
                 paths_book: PathsBook,
                 on_projects_count_update: OnProjectsCountUpdate,
                 context: Context
                 ):
        super().__init__()
        self.paths = paths
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update
        self.ignored_patterns = ignored_patterns + [f"{p}/**" for p in ignored_patterns]
        self.context = context
        asyncio.run(self.reload())

    async def reload(self):

        results = [auto_detect_projects(paths_book=self.paths_book, root_folder=root_folder,
                                        ignore=self.ignored_patterns)
                   for root_folder in self.paths]

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

        if not any(isinstance(event, Type) for Type in [DirCreatedEvent, DirDeletedEvent]):
            return None
        path = event.src_path

        if Path(path).name != '.yw_pipeline':
            return None
        # we should also ignore the PathBook.database and PathBook.system
        # make Projects.finder.ignoredPattern a function
        ignored = any(fnmatch.fnmatch(path, pattern) for pattern in self.ignored_patterns)
        if ignored:
            return None

        return Path(path).parent


class RecursiveProjectsFinderThread(Thread):

    paths: List[Path]
    ignored_patterns = List[str]
    paths_book: PathsBook
    on_projects_count_update: OnProjectsCountUpdate

    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    event_handler: RecursiveFinderEventHandler

    stopped = False

    def __init__(self, paths: List[Path], ignored_patterns: List[str], paths_book: PathsBook,
                 on_projects_count_update: OnProjectsCountUpdate):
        super().__init__()
        self.paths = paths
        self.ignored_patterns = ignored_patterns
        self.paths_book = paths_book
        self.on_projects_count_update = on_projects_count_update

    def go(self):
        self.start()

    def join(self, timeout=0):
        self.stopped = True

    def run(self) -> None:

        observer = Observer()
        self.event_handler = RecursiveFinderEventHandler(
            paths=self.paths,
            ignored_patterns=self.ignored_patterns,
            paths_book=self.paths_book,
            on_projects_count_update=self.on_projects_count_update,
            context=self.context
        )

        for folder in self.paths:
            if not Path(folder).exists():
                continue
            observer.schedule(self.event_handler, str(folder), recursive=True)

        observer.start()

        log_info(f"RecursiveProjectsFinderThread started, folders: {[f'{p}' for p in self.paths]}")
        while not self.stopped:
            time.sleep(1)
        observer.stop()
        observer.join()
        # super().join()
