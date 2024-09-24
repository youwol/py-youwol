# typing
from typing import Any

# relative
from .models.defaults import default_auth_provider, default_platform_host
from .models.model_remote import Authentication
from .models.models_config import AuthorizationProvider, BrowserAuth, CloudEnvironment


def get_standard_auth_provider(host: str, **kwargs: Any) -> AuthorizationProvider:
    """
    Configuration for a standard YouWol installation.

    Parameters:
        host: host of the installation (e.g. platform.youwol.com)
        kwargs: overriding attributes for `AuthorizationProvider` construction.
    Returns: The configuration
    """
    return AuthorizationProvider(**{**default_auth_provider(host), **kwargs})


def get_standard_youwol_env(
    env_id: str,
    host: str | None = None,
    authentications: list[Authentication] | None = None,
    **kwargs: Any,
) -> CloudEnvironment:
    """
    Construct a `CloudEnvironment` using YouWol's standard auth. provider.

    Parameters:
        env_id: ID of the environment
        host: Target host or default to
            :attr:`default_platform_host <youwol.app.environment.models.defaults.default_platform_host>`
        authentications: List of authentications available, default to `[BrowserAuth(authId="browser")]`
        kwargs: arguments forwarded to
            :func:`get_standard_auth_provider <youwol.app.environment.online_environments.get_standard_auth_provider>`.

    Returns:
        The cloud environment.
    """
    host = host or default_platform_host
    authentications = authentications or [BrowserAuth(authId="browser")]
    return CloudEnvironment(
        envId=env_id,
        host=host,
        authProvider=get_standard_auth_provider(host=host, **kwargs),
        authentications=authentications,
    )
