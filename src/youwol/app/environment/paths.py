# standard library
from importlib import resources
from pathlib import Path

# third parties
from appdirs import AppDirs
from pydantic import BaseModel

# Youwol application
from youwol.app.main_args import get_main_arguments

# Youwol utilities
from youwol.utils.utils_paths import existing_path_or_default

# relative
from .models import predefined_configs


class PathsBook(BaseModel):
    """
    References usual paths (folders or files) used by youwol.
    """

    config: Path
    """
    The path of the configuration file
    """

    system: Path
    """
    The path of folder that includes system related data (e.g. cache).
    """

    databases: Path
    """
    The path of root folder representing user's data.
    """

    @property
    def local_storage(self) -> Path:
        """

        Return:
            The path of the root storage (for files) of user's data.
        """
        return self.databases / "storage"

    @property
    def local_cdn_storage(self) -> Path:
        """

        Return:
            The path of the CDN database for files.
        """
        return self.local_storage / "cdn" / "youwol-users"

    def local_cdn_component(self, name: str, version: str) -> Path:
        """
        Parameters:
            name: Name of the package
            version: Version of the package
        Return:
            The folder path associated to the component in the CDN database.
        """
        return self.local_cdn_storage / "libraries" / name / version

    @property
    def local_stories_storage(self) -> Path:
        return self.local_storage / "stories" / "youwol-users"

    @property
    def js_modules_store_path(self) -> Path:
        return self.system / "node_modules"

    def cdn_zip_path(self, name: str, version: str) -> Path:
        return self.store_node_module(name) / (version + ".zip")

    @property
    def packages_cache_filename(self) -> str:
        return "packages-cache.json"

    @property
    def packages_cache_path(self) -> Path:
        return self.js_modules_store_path / self.packages_cache_filename

    @property
    def store_node_modules(self) -> Path:
        return self.js_modules_store_path

    def store_node_module(self, target_name: str) -> Path:
        if "/" in target_name:
            namespace, name = target_name.split("/")
            return self.store_node_modules / namespace / name

        return self.store_node_modules / target_name

    @staticmethod
    def node_modules(target_folder: Path | str) -> Path:
        return Path(target_folder) / "node_modules"

    @classmethod
    def node_module_dependency(
        cls, target_folder: Path | str, dependency_name: str
    ) -> Path:
        if "/" in dependency_name:
            namespace, name = dependency_name.split("/")
            return cls.node_modules(target_folder) / namespace / name

        return cls.node_modules(target_folder) / dependency_name

    def artifacts_flow(self, project_name: str, flow_id: str) -> Path:
        """
        Return the parent folder that includes all artifacts related files of a given project and flow.

        Parameters:
            project_name: name of the project.
            flow_id: id of the flow.
        Return:
            The path of the parent folder.
        """
        return self.system / project_name / flow_id

    def artifacts_step(self, project_name: str, flow_id: str, step_id: str) -> Path:
        """
        Return the parent folder that includes all artifacts related files of a given project, given flow
        and given step.

        Parameters:
            project_name: name of the project.
            flow_id: id of the flow.
            step_id: id of the step.
        Return:
            The path of the parent folder.
        """

        return self.artifacts_flow(project_name=project_name, flow_id=flow_id) / step_id

    def artifact(
        self, project_name: str, flow_id: str, step_id: str, artifact_id: str
    ) -> Path:
        """
        Return the path of the parent folder that includes all artifacts related files of a given project, flow
        , step and artifact.

        Parameters:
            project_name: name of the project.
            flow_id: id of the flow.
            step_id: id of the step.
            artifact_id: id of the artifact.
        Return:
            The path of the parent folder.
        """

        return (
            self.artifacts_step(
                project_name=project_name, flow_id=flow_id, step_id=step_id
            )
            / f"artifact-{artifact_id}"
        )

    def artifacts_manifest(self, project_name: str, flow_id: str, step_id: str):
        """
        Return the path of the manifest file of a given project, flow and step.

        Parameters:
            project_name: name of the project.
            flow_id: id of the flow.
            step_id: id of the step.
        Return:
            The path of the manifest file.
        """

        return (
            self.artifacts_step(
                project_name=project_name, flow_id=flow_id, step_id=step_id
            )
            / "manifest.json"
        )

    def __str__(self):
        return f"""
 * config file: {self.config}
 * databases directory: {self.databases}
 * system directory: {self.system}
"""


app_dirs = AppDirs(appname="py-youwol", appauthor="Youwol")


def ensure_config_file_exists_or_create_it(path: Path | None) -> (Path, bool):
    path = path if path else Path("config.py")
    (final_path, exists) = existing_path_or_default(
        path,
        root_candidates=[Path().cwd(), app_dirs.user_config_dir, Path().home()],
        default_root=app_dirs.user_config_dir,
    )
    if not exists:
        args = get_main_arguments()

        if args.config_path is not None:
            final_path = args.config_path
            if args.init is False:
                msg = f"configuration file '{final_path}' does not exists. Pass the --init flag to create it"
                raise RuntimeError(msg)

        final_path.parent.mkdir(parents=True, exist_ok=True)

        content = (
            resources.files(predefined_configs)
            .joinpath("default_config.py")
            .read_text(encoding="UTF-8")
        )
        final_path.write_text(data=content, encoding="UTF-8")

    return final_path, exists
