from pathlib import Path

from youwol.configuration.models_config import Configuration
from youwol.environment.configuration_handler import ConfigurationHandler
from youwol.environment.paths import app_dirs
from youwol_utils.utils_paths import PathException, existing_path_or_default


class ConfigurationStaticFile(Configuration):
    pass


async def configuration_from_json(path: Path) -> ConfigurationHandler:
    (final_path, exists) = existing_path_or_default(path,
                                                    root_candidates=[Path().cwd(),
                                                                     app_dirs.user_config_dir,
                                                                     Path().home()],
                                                    default_root=app_dirs.user_config_dir)

    if not exists:
        raise PathException(f"{str(final_path)} does not exists")

    if not final_path.is_file():
        raise PathException(f"'{str(final_path)}' is not a file")

    config_data = ConfigurationStaticFile.parse_file(final_path)

    return ConfigurationHandler(path=final_path, config_data=config_data)
