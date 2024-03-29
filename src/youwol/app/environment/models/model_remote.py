"""
This file gathers [configuration](@yw-nav-class:models_config.Configuration)'s models related to remote environments
and authorizations.
"""

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import PrivateClient, PublicClient


class AuthorizationProvider(BaseModel):
    """
    Authorization provider.
    """

    openidBaseUrl: str
    """
    OpenId base URL.
    """

    openidClient: PrivateClient | PublicClient
    """
    openId client.
    """


class Authentication(BaseModel):
    """
    Virtual base class for authentication modes.

    See
    [BrowserAuth](@yw-nav-class:BrowserAuth) or
    [DirectAuth](@yw-nav-class:DirectAuth)
    """

    authId: str
    """
    Unique id of the authentication for encapsulating in
    [CloudEnvironment](@yw-nav-class:CloudEnvironment).
    """


class BrowserAuth(Authentication):
    """
    Authentication using the browser with cookies: the browser automatically handle authentication (eventually
    redirecting to the login page if needed).
    """


class DirectAuth(Authentication):
    """
    Authentication using direct-flow.
    """

    userName: str
    """
    Credential's user-name.
    """

    password: str
    """
    Credential's password.
    """


class CloudEnvironment(BaseModel):
    """
    Specification of a remote YouWol environment.

    Example:
        The standard youwol cloud environment connected using a browser connection or a direct connection:

        <code-snippet language="python">
        from pathlib import Path

        from youwol.app.environment import (
            Configuration,
            System,
            CloudEnvironments,
            DirectAuth,
            BrowserAuth,
            CloudEnvironment,
            get_standard_auth_provider,
        )

        environment = CloudEnvironment(
            envId="youwol",
            host="platform.youwol.com",
            authProvider=get_standard_auth_provider("platform.youwol.com"),
            authentications=[
                BrowserAuth(authId="browser"),
                DirectAuth(authId="bar", userName="bar", password="bar-pwd"),
            ],
        )
        </code-snippet>
    """

    envId: str
    """
    Unique id for this environment.
    """

    host: str
    """
    Host of the environment (e.g. `platform.youwol.com`).
    """

    authProvider: AuthorizationProvider
    """
    Specification of the authorization provider.

    For a Keycloak authentication provider including a properly configured `youwol` realm, the function
     [default_auth_provider](@yw-nav-func:default_auth_provider) is available.
    """

    authentications: list[Authentication]
    """
    List of accepted authentications for the environment.
    """


class Connection(BaseModel):
    """
    A connection is the association of an environment id and an authentication id.
    """

    envId: str
    """
    Reference an environment ID provided in
     [CloudEnvironments](@yw-nav-attr:CloudEnvironments.environments).
    """

    authId: str
    """
    Reference an authentication ID provided in the
     [CloudEnvironment](@yw-nav-class:CloudEnvironment) with ID `envId`.
    """


class CloudEnvironments(BaseModel):
    """
    Cloud environments on which connection can be established.

    At a particular time, py-youwol is connected to one cloud environment.
    This is where missing assets (data, libraries, backends) are retrieved.

    Example:
        Below is an example declaring 2 cloud environments, one related to a hypothetical remote environment of
        a company `foo`, and the second the regular youwol remote environment :
        <code-snippet language="python">

        from pathlib import Path

        from youwol.app.environment import (
            Configuration,
            System,
            CloudEnvironments,
            LocalEnvironment,
            DirectAuth,
            BrowserAuth,
            CloudEnvironment,
            get_standard_auth_provider,
            Connection,
            get_standard_youwol_env,
        )

        company_name = "foo"
        foo_cloud = CloudEnvironment(
            envId=company_name,
            host=f"platform.{company_name}.com",
            authProvider=get_standard_auth_provider(f"platform.{company_name}.com"),
            authentications=[
                BrowserAuth(authId="browser"),
                DirectAuth(authId="bar", userName="bar", password="bar-pwd"),
            ]
        )


        Configuration(
            system=System(
                cloudEnvironments=CloudEnvironments(
                    defaultConnection=Connection(envId=company_name, authId="bar"),
                    environments=[
                        foo_cloud,
                        get_standard_youwol_env(env_id="public-youwol"),
                    ],
                )
            )
        )
        <code-snippet>
    """

    defaultConnection: Connection
    """
    Connection used when py-youwol is started.

    To switch connection after youwol has started, see end-point
     [Login](@yw-nav-func:login).
    """

    environments: list[CloudEnvironment]
    """
    Available (YouWol) cloud environments with which youwol can connect.
    """
