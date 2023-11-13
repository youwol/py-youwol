# standard library
import os

# typing
from typing import Optional

# third parties
from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Configuration:
    version: str
    oidc_issuer: str
    client_id: str
    client_secret: str
    assets_gateway_base_url: str
    config_id: str
    host: str
    default_cdn_client_version: str
    default_webpm_client_version: str
    root_redirection: str


class ConfigurationFactory:
    __configuration: Optional[Configuration] = None

    @classmethod
    def get(cls) -> Configuration:
        if ConfigurationFactory.__configuration is None:
            raise ValueError(
                "ConfigurationFactory.get() invoked before ConfigurationFactory.set()"
            )
        return ConfigurationFactory.__configuration

    @classmethod
    def set(cls, configuration: Configuration):
        if cls.__configuration is not None:
            raise ValueError("ConfigurationFactory.set() invoked twice")
        cls.__configuration = configuration

    @classmethod
    def set_from_env(cls):
        cls.set(
            Configuration(
                version=os.environ.get("VERSION"),
                oidc_issuer=os.environ.get("OIDC_ISSUER"),
                client_id=os.environ.get("CLIENT_ID"),
                client_secret=os.environ.get("CLIENT_SECRET"),
                assets_gateway_base_url=os.environ.get("ASSETS_GATEWAY_BASE_URL"),
                config_id=os.environ.get("CONFIG_ID"),
                host=os.environ.get("HOST"),
                default_cdn_client_version=os.environ.get("DEFAULT_CDN_CLIENT_VERSION"),
                default_webpm_client_version=os.environ.get(
                    "DEFAULT_WEBPM_CLIENT_VERSION"
                ),
                root_redirection=os.environ.get("ROOT_REDIRECTION"),
            )
        )
