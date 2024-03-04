# standard library
import os

# third parties
from pydantic.dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Configuration:
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
    __configuration: Configuration | None = None

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
    def set_from_env(cls) -> None:
        cls.set(
            Configuration(
                oidc_issuer=cls.__get_value_from_env("OIDC_ISSUER"),
                client_id=cls.__get_value_from_env("CLIENT_ID"),
                client_secret=cls.__get_value_from_env("CLIENT_SECRET"),
                assets_gateway_base_url=cls.__get_value_from_env(
                    "ASSETS_GATEWAY_BASE_URL"
                ),
                config_id=cls.__get_value_from_env("CONFIG_ID"),
                host=cls.__get_value_from_env("HOST"),
                default_cdn_client_version=cls.__get_value_from_env(
                    "DEFAULT_CDN_CLIENT_VERSION"
                ),
                default_webpm_client_version=cls.__get_value_from_env(
                    "DEFAULT_WEBPM_CLIENT_VERSION"
                ),
                root_redirection=cls.__get_value_from_env("ROOT_REDIRECTION"),
            )
        )

    @staticmethod
    def __get_value_from_env(key) -> str:
        v = os.environ.get(key)
        if v is None:
            raise ValueError(f"Missing environment value {key}")
        return v
