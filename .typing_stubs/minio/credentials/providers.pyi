# standard library
import abc

from abc import ABCMeta, abstractmethod

# third parties
from _typeshed import Incomplete
from minio.helpers import sha256_hash as sha256_hash
from minio.signer import sign_v4_sts as sign_v4_sts
from minio.time import from_iso8601utc as from_iso8601utc
from minio.time import to_amz_date as to_amz_date
from minio.time import utcnow as utcnow
from minio.xml import find as find
from minio.xml import findtext as findtext

# relative
from .credentials import Credentials as Credentials

class Provider(metaclass=abc.ABCMeta):
    __metaclass__ = ABCMeta
    @abstractmethod
    def retrieve(self): ...

class AssumeRoleProvider(Provider):
    def __init__(
        self,
        sts_endpoint,
        access_key,
        secret_key,
        duration_seconds: int = ...,
        policy: Incomplete | None = ...,
        region: Incomplete | None = ...,
        role_arn: Incomplete | None = ...,
        role_session_name: Incomplete | None = ...,
        external_id: Incomplete | None = ...,
        http_client: Incomplete | None = ...,
    ) -> None: ...
    def retrieve(self): ...

class ChainedProvider(Provider):
    def __init__(self, providers) -> None: ...
    def retrieve(self): ...

class EnvAWSProvider(Provider):
    def retrieve(self): ...

class EnvMinioProvider(Provider):
    def retrieve(self): ...

class AWSConfigProvider(Provider):
    def __init__(
        self, filename: Incomplete | None = ..., profile: Incomplete | None = ...
    ) -> None: ...
    def retrieve(self): ...

class MinioClientConfigProvider(Provider):
    def __init__(
        self, filename: Incomplete | None = ..., alias: Incomplete | None = ...
    ) -> None: ...
    def retrieve(self): ...

class IamAwsProvider(Provider):
    def __init__(
        self,
        custom_endpoint: Incomplete | None = ...,
        http_client: Incomplete | None = ...,
    ) -> None: ...
    def fetch(self, url): ...
    def retrieve(self): ...

class LdapIdentityProvider(Provider):
    def __init__(
        self,
        sts_endpoint,
        ldap_username,
        ldap_password,
        http_client: Incomplete | None = ...,
    ) -> None: ...
    def retrieve(self): ...

class StaticProvider(Provider):
    def __init__(
        self, access_key, secret_key, session_token: Incomplete | None = ...
    ) -> None: ...
    def retrieve(self): ...

class WebIdentityClientGrantsProvider(Provider, metaclass=abc.ABCMeta):
    __metaclass__ = ABCMeta
    def __init__(
        self,
        jwt_provider_func,
        sts_endpoint,
        duration_seconds: int = ...,
        policy: Incomplete | None = ...,
        role_arn: Incomplete | None = ...,
        role_session_name: Incomplete | None = ...,
        http_client: Incomplete | None = ...,
    ) -> None: ...
    def retrieve(self): ...

class ClientGrantsProvider(WebIdentityClientGrantsProvider):
    def __init__(
        self,
        jwt_provider_func,
        sts_endpoint,
        duration_seconds: int = ...,
        policy: Incomplete | None = ...,
        http_client: Incomplete | None = ...,
    ) -> None: ...

class WebIdentityProvider(WebIdentityClientGrantsProvider): ...

class CertificateIdentityProvider(Provider):
    def __init__(
        self,
        sts_endpoint,
        cert_file: Incomplete | None = ...,
        key_file: Incomplete | None = ...,
        key_password: Incomplete | None = ...,
        ca_certs: Incomplete | None = ...,
        duration_seconds: int = ...,
        http_client: Incomplete | None = ...,
    ) -> None: ...
    def retrieve(self): ...
