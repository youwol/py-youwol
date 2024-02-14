# typing

# relative
from .models.defaults import default_auth_provider, default_platform_host
from .models.model_remote import Authentication
from .models.models_config import AuthorizationProvider, BrowserAuth, CloudEnvironment


def get_standard_auth_provider(host: str, **kwargs) -> AuthorizationProvider:
    """
    Configuration for a standard YouWol installation.

    :param host: host of the installation (e.g. platform.youwol.com)
    :return: The configuration
    """
    return AuthorizationProvider(**{**default_auth_provider(host), **kwargs})


def get_standard_youwol_env(
    env_id: str,
    host: str | None = None,
    authentications: list[Authentication] | None = None,
    **kwargs,
) -> CloudEnvironment:
    host = host or default_platform_host
    authentications = authentications or [BrowserAuth(authId="browser")]
    return CloudEnvironment(
        envId=env_id,
        host=host,
        authProvider=get_standard_auth_provider(host=host, **kwargs),
        authentications=authentications,
    )
