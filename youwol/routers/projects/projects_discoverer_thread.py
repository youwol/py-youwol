import asyncio
import fnmatch
import time
import traceback
from pathlib import Path
from threading import Thread
from typing import List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, DirDeletedEvent, FileSystemEvent
from youwol.environment import YouwolEnvironment, ImplicitProjectsFinder
from youwol.routers.environment import ProjectsLoadingResults
from youwol.routers.projects import get_project, ProjectLoader, Project
from youwol.web_socket import WsDataStreamer
from youwol_utils import log_info, Context


def start_project_discoverer(env: YouwolEnvironment):

    if isinstance(env.projects.finder, ImplicitProjectsFinder) and env.projects.finder.watch:
        projects_discoverer_thread = ProjectsDiscovererThread(
            finder=env.projects.finder,
            env=env
        )
        try:
            projects_discoverer_thread.go()
        except RuntimeError as e:
            print("Error while starting projects discoverer thread")
            print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
            raise e


class ProjectsEventHandler(FileSystemEventHandler):
    """Logs all the events captured."""
    env: YouwolEnvironment
    context: Context
    current_projects: List[Project]
    ignored_patterns: List[str]

    def __init__(self,
                 initial_projects: List[Project],
                 ignored_patterns: List[str],
                 env: YouwolEnvironment,
                 context: Context
                 ):
        super().__init__()
        self.env = env
        self.ignored_patterns = ignored_patterns + [f"{p}/**" for p in ignored_patterns]
        self.context = context
        self.current_projects = initial_projects

    def on_created(self, event: FileSystemEvent):
        super().on_created(event)
        project_path = self.project_path(event)
        if project_path:
            async def add_project():
                project = await get_project(
                    project_path=Path(event.src_path).parent,
                    additional_python_src_paths=[],
                    env=self.env,
                    context=self.context)
                self.current_projects = [*self.current_projects, project]
                results = ProjectsLoadingResults(results=self.current_projects)
                await self.context.send(results)
                self.env.cache_py_youwol["ProjectLoader"] = self.current_projects

            asyncio.run(add_project())

    def on_deleted(self, event):
        super().on_deleted(event)
        project_path = self.project_path(event)
        if project_path:
            async def remove_project():
                self.current_projects = [p for p in self.current_projects if p.path != project_path]
                results = ProjectsLoadingResults(results=self.current_projects)
                await self.context.send(results)
                self.env.cache_py_youwol["ProjectLoader"] = self.current_projects

            asyncio.run(remove_project())

    def project_path(self, event: FileSystemEvent) -> Optional[Path]:

        if not any(isinstance(event, Type) for Type in [DirCreatedEvent, DirDeletedEvent]):
            return None
        path = event.src_path

        if Path(path).name != '.yw_pipeline':
            return None

        ignored = any(fnmatch.fnmatch(path, pattern) for pattern in self.ignored_patterns)
        if ignored:
            return None

        return Path(path).parent


class ProjectsDiscovererThread(Thread):

    finder: ImplicitProjectsFinder
    env: YouwolEnvironment

    context = Context(logs_reporters=[], data_reporters=[WsDataStreamer()])

    def __init__(self, finder: ImplicitProjectsFinder, env: YouwolEnvironment):
        super().__init__()
        self.finder = finder
        self.env = env

    def go(self):
        self.start()

    def join(self, timeout=0):
        if self.is_alive():
            super().join()

    def run(self) -> None:

        async def load_projects_and_watch():
            projects = await ProjectLoader.get_projects(
                env=self.env,
                context=self.context
            )
            log_info(f"retrieved {len(projects)} projects")
            await self.context.send(ProjectsLoadingResults(results=projects))

            observer = Observer()
            event_handler = ProjectsEventHandler(
                initial_projects=projects,
                ignored_patterns=self.finder.ignorePatterns,
                env=self.env,
                context=self.context
            )
            for folder in self.finder.fromPaths:
                if not folder.exists():
                    continue
                observer.schedule(event_handler, str(folder), recursive=True)
            observer.start()
            log_info("Projects discoverer launched")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()

            return projects

        asyncio.run(load_projects_and_watch())
