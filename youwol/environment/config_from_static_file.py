from pathlib import Path
from typing import Optional, Dict

from youwol.environment.configuration_handler import ConfigurationHandler
from youwol.configuration.models_config import Profiles, ConfigurationData, Cascade, CascadeBaseProfile, \
    ExtendingProfile
from youwol.environment.paths import app_dirs
from youwol_utils.utils_paths import PathException, existing_path_or_default


class ConfigurationDataWithCascade(ConfigurationData):
    cascade: Cascade = CascadeBaseProfile.REPLACE


class ConfigurationStaticFile(ConfigurationData):
    extending_profiles: Dict[str, ConfigurationDataWithCascade] = {}
    selected_profile: str = "default"


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
                           extending_profiles={key: ExtendingProfile(config_data=profile,
                                                                     cascade=profile.cascade)
                                               for (key, profile) in config_data.extending_profiles.items()},
                           selected=config_data.selected_profile)

    return ConfigurationHandler(path=final_path, config_data=config_data, profile=profile)
