# Youwol application
from youwol.app.environment.local_auth import local_tokens_id
from youwol.app.environment.youwol_environment import yw_config

# Youwol backends
import youwol.backends.accounts

# Youwol utilities
from youwol.utils import CacheClient, OidcConfig
from youwol.utils.context import ContextFactory


async def cdn_config_py_youwol():
    return (await yw_config()).backends_configuration.cdn_backend


async def tree_db_config_py_youwol():
    return (await yw_config()).backends_configuration.tree_db_backend


async def assets_backend_config_py_youwol():
    return (await yw_config()).backends_configuration.assets_backend


async def flux_backend_config_py_youwol():
    return (await yw_config()).backends_configuration.flux_backend


async def assets_gtw_config_py_youwol():
    return (await yw_config()).backends_configuration.assets_gtw


async def stories_config_py_youwol():
    return (await yw_config()).backends_configuration.stories_backend


async def cdn_apps_server_config_py_youwol():
    return (await yw_config()).backends_configuration.cdn_apps_server


async def cdn_session_storage_config_py_youwol():
    return (await yw_config()).backends_configuration.cdn_sessions_storage


async def files_backend_config_py_youwol():
    return (await yw_config()).backends_configuration.files_backend


async def accounts_backend_config_py_youwol():
    config = await yw_config()
    auth_cache: CacheClient = ContextFactory.with_static_data["auth_cache"]

    auth_provider = config.get_remote_info().authProvider

    oidc_config = OidcConfig(auth_provider.openidBaseUrl)

    return youwol.backends.accounts.Configuration(
        openid_client=oidc_config.for_client(
            config.get_remote_info().authProvider.openidClient
        ),
        auth_cache=auth_cache,
        https=False,
        tokens_id_generator=lambda: local_tokens_id(
            auth_provider=config.get_remote_info().authProvider,
            auth_infos=config.get_authentication_info(),
        ),
        tokens_storage=config.tokens_storage,
    )
