from pathlib import Path

from youwol.configuration.models_config import JwtSource, Projects
from youwol.environment.config_from_module import IConfigurationFactory, Configuration
from youwol.environment.utils import auto_detect_projects
from youwol.main_args import MainArguments

youwol_projects = Path.home() / 'Projects'


class ConfigurationFactory(IConfigurationFactory):

    async def get(self, main_args: MainArguments) -> Configuration:
        return Configuration(
            jwtSource=JwtSource.CONFIG,
            projects=Projects(
                finder=lambda env, _ctx: auto_detect_projects(
                    env=env,
                    root_folder=youwol_projects,
                )
            ),

        )
