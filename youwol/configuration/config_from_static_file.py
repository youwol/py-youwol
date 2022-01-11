from pathlib import Path
from typing import Optional, Dict

from youwol.configuration.configuration_handler import ConfigurationHandler
from youwol.configuration.models_config import Profiles, ConfigurationData, Cascade, ConfigurationProfileCascading, \
    CascadeBaseProfile
from youwol.utils_paths import app_dirs, PathException, existing_path_or_default


class ConfigurationOtherProfile(ConfigurationData):
    cascade: Cascade = CascadeBaseProfile.REPLACE


class ConfigurationStaticFile(ConfigurationData):
    others: Dict[str, ConfigurationOtherProfile]
    profile: str = "default"


async def configuration_from_json(path: Path, profile: Optional[str]) -> ConfigurationHandler:
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

    config_data = Profiles(default=config_data,
                           others={key: ConfigurationProfileCascading(config_data=other, cascade=other.cascade)
                                   for (key, other) in config_data.others.items()},
                           selected=config_data.profile)

    return ConfigurationHandler(path=final_path, config_data=config_data, profile=profile)
