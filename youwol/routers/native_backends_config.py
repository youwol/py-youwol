import youwol_accounts
from youwol.environment.youwol_environment import yw_config
from youwol_utils import CacheClient
from youwol_utils.context import ContextFactory


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
    pkce_cache: CacheClient = ContextFactory.with_static_data['accounts_pkce_cache']
    jwt_cache: CacheClient = ContextFactory.with_static_data['jwt_cache']
    return youwol_accounts.Configuration(
        openid_base_url=config.get_remote_info().authProvider.openidBaseUrl,
        openid_client=config.get_remote_info().authProvider.openidClient,
        admin_client=config.get_remote_info().authProvider.keycloakAdminClient,
        keycloak_admin_base_url=config.get_remote_info().authProvider.keycloakAdminBaseUrl,
        jwt_cache=jwt_cache,
        pkce_cache=pkce_cache
    )


async def mock_backend_config_py_youwol():
    return (await yw_config()).backends_configuration.mock_backend
