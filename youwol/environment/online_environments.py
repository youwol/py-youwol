from typing import List, Optional
from youwol.environment.models.defaults import default_auth_provider, default_platform_host
from youwol.environment.models.models_config import AuthorizationProvider, CloudEnvironment, BrowserAuth, Authentication


def get_standard_auth_provider(host: str, **kwargs) -> AuthorizationProvider:
    """
    Configuration for a standard YouWol installation.

    :param host: host of the installation (e.g. platform.youwol.com)
    :return: The configuration
    """
    return AuthorizationProvider(**{**default_auth_provider(host), **kwargs})


def get_standard_youwol_env(
        env_id: str,
        host: Optional[str] = None,
        authentications: Optional[List[Authentication]] = None,
        **kwargs
) -> CloudEnvironment:
    host = host or default_platform_host
    authentications = authentications or [BrowserAuth(authId='browser')]
    return CloudEnvironment(
        envId=env_id,
        host=host,
        authProvider=get_standard_auth_provider("platform.youwol.com", **kwargs),
        authentications=authentications
    )
