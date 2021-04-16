import pprint
from pathlib import Path
from typing import Union, Dict, Any

from youwol.configuration.configuration_validation import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    safe_load
    )
from youwol.configuration.models_base import ErrorResponse
from youwol.configurations import get_full_local_config

from youwol.context import Context, Action
from youwol.main_args import get_main_arguments
from youwol.configuration.user_configuration import YouwolConfiguration
from youwol.models import ActionStep


class YouwolConfigurationFactory:

    __cached_config: YouwolConfiguration = None

    @staticmethod
    async def switch(path: Union[str, Path],
                     context: Context) -> ConfigurationLoadingStatus:

        async with context.start(Action.SWITCH_CONF) as ctx:
            path = Path(path)
            conf, status = await safe_load(path=path, params_values={})
            if not conf:
                errors = [c.dict() for c in status.checks if isinstance(c.status, ErrorResponse)]
                await ctx.abort(content='Failed to switch configuration',
                                json={
                                    "first error": next(e for e in errors),
                                    "errors": errors,
                                    "all checks": [c.dict() for c in status.checks]})
                return status
            await ctx.info(step=ActionStep.STATUS, content='Switched to new conf. successful', json=status.dict())
            YouwolConfigurationFactory.__cached_config = conf
        return status

    @staticmethod
    async def get():
        cached = YouwolConfigurationFactory.__cached_config
        config = cached or await YouwolConfigurationFactory.init()
        return config

    @staticmethod
    async def reload(params_values: Dict[str, Any] = None):

        params_values = params_values or {}
        cached = YouwolConfigurationFactory.__cached_config
        params_values = {**cached.configurationParameters.get_values(), **params_values}
        conf, status = await safe_load(
            path=cached.pathsBook.config_path,
            params_values=params_values,
            user_email=cached.userEmail
            )
        if not conf:
            return status

        YouwolConfigurationFactory.__cached_config = conf
        return status

    @staticmethod
    async def login(email: str):
        conf = YouwolConfigurationFactory.__cached_config
        new_conf = YouwolConfiguration(
            userConfig=conf.userConfig,
            userEmail=email,
            pathsBook=conf.pathsBook,
            localClients=conf.localClients,
            configurationParameters=conf.configurationParameters,
            http_port=get_main_arguments().port,
            cache={}
            )
        YouwolConfigurationFactory.__cached_config = new_conf
        return new_conf

    @staticmethod
    async def init():
        path = (await get_full_local_config()).starting_yw_config_path
        conf, status = await safe_load(path=path, params_values={})
        if not conf:
            for check in status.checks:
                if isinstance(check.status, ErrorResponse):
                    pprint.pprint(check)
            raise ConfigurationLoadingException(status)

        YouwolConfigurationFactory.__cached_config = conf
        return YouwolConfigurationFactory.__cached_config

    @staticmethod
    def clear_cache():

        conf = YouwolConfigurationFactory.__cached_config
        new_conf = YouwolConfiguration(
            userConfig=conf.userConfig,
            userEmail=conf.userEmail,
            pathsBook=conf.pathsBook,
            localClients=conf.localClients,
            configurationParameters=conf.configurationParameters,
            http_port=get_main_arguments().port,
            cache={}
            )
        YouwolConfigurationFactory.__cached_config = new_conf


async def yw_config() -> YouwolConfiguration:
    return await YouwolConfigurationFactory.get()
