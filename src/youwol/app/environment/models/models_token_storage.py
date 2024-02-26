"""
This file gathers [TokensStorageConf](@yw-nav-class:models_token_storage.TokensStorageConf) related models of the
[configuration](@yw-nav-class:models_config.Configuration).
"""

# standard library
from abc import ABC, abstractmethod
from pathlib import Path

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment.models.defaults import (
    default_path_tokens_storage,
    default_path_tokens_storage_encrypted,
)

# Youwol utilities
from youwol.utils.clients.oidc.tokens_manager import TokensStorageCache
from youwol.utils.context import ContextFactory

# relative
from .tokens_storage.encrypted_file import AlgoSpec, TokensStorageKeyring
from .tokens_storage.file import TokensStorageFile


class TokensStorageConf(ABC):
    """
    Abstract class for tokens storage.
    """

    @abstractmethod
    async def get_tokens_storage(self):
        pass


class TokensStorageSystemKeyring(TokensStorageConf, BaseModel):
    """
    Tokens storage using system's keyring.
    """

    path: str | Path | None = default_path_tokens_storage_encrypted
    """
    The path of the system keyring encrypted file.

    See <a href="@yw-nav-glob:default_path_tokens_storage_encrypted">
    default_path_tokens_storage_encrypted</a>
    regarding default value.
    """

    service: str = "py-youwol"
    """
    Service name.
    """

    algo: AlgoSpec = "any"
    """
    Algorithm used for encryption.
    """

    async def get_tokens_storage(self):
        path = self.path if isinstance(self.path, Path) else Path(self.path)
        result = TokensStorageKeyring(
            service=self.service, absolute_path=path, algo=self.algo
        )
        await result.load_data()
        return result


class TokensStoragePath(TokensStorageConf, BaseModel):
    """
    Tokens storage using a TokensStorageFile.
    """

    path: str | Path | None = default_path_tokens_storage
    """
    Path where the file is saved on disk.

    See [default_path_tokens_storage](@yw-nav-glob:default_path_tokens_storage)
     regarding default value.
    """

    async def get_tokens_storage(self):
        path = self.path if isinstance(self.path, Path) else Path(self.path)
        result = TokensStorageFile(path)
        await result.load_data()
        return result


class TokensStorageInMemory(TokensStorageConf):
    """
    In memory tokens storage.
    """

    async def get_tokens_storage(self):
        return TokensStorageCache(cache=ContextFactory.with_static_data["auth_cache"])
