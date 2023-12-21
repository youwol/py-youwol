# standard library
from io import StringIO
from pathlib import Path

# typing
from typing import Literal, Optional, Union

# third parties
import keyring

# Youwol utilities
from youwol.utils.crypto.file_encryption import (
    Algo,
    FileEncryptionException,
    decrypt_from_file,
    encrypt_into_file,
    generate_key,
)

# relative
from .path_base import (
    PathBase,
    ReaderBase,
    TokensStoragePathBase,
    TokensStoragePathBaseException,
    WriterBase,
)

AlgoSpec = Union[Literal["any"], Optional[Algo]]
"""
Encryption algorithm.
"""


class EncryptedFileReader(ReaderBase):
    def __init__(
        self,
        absolute_path: Path,
        key: str,
        algo: Optional[AlgoSpec] = None,
    ):
        try:
            if algo == "any":
                data = decrypt_from_file(
                    path=absolute_path, key=key, expected_algo=None
                )
            elif algo is not None:
                data = decrypt_from_file(
                    path=absolute_path, key=key, expected_algo=algo
                )
            else:
                data = decrypt_from_file(path=absolute_path, key=key)
        except FileEncryptionException as e:
            raise TokensStoragePathBaseException(e)
        self.__string_io = StringIO(initial_value=data)

    def read(self, *args, **kwargs) -> str:
        return self.__string_io.read(*args, **kwargs)

    def _close(self):
        return self.__string_io.close()


class EncryptedFileWriter(WriterBase):
    def __init__(
        self,
        absolute_path: Path,
        key: str,
        algo: Optional[AlgoSpec] = None,
    ):
        self.__path = absolute_path
        self.__key = key
        self.__algo = algo
        self.__string_io = StringIO()

    def write(self, *args, **kwargs) -> int:
        return self.__string_io.write(*args, **kwargs)

    def _exit_without_exception(self):
        data = self.__string_io.getvalue()
        try:
            if self.__algo is not None and self.__algo != "any":
                encrypt_into_file(
                    data, path=self.__path, key=self.__key, algo=self.__algo
                )
            else:
                encrypt_into_file(data, path=self.__path, key=self.__key)
        except FileEncryptionException as e:
            raise TokensStoragePathBaseException(e)

    def _close(self):
        return self.__string_io.close()


class EncryptedFilePath(PathBase):
    def __init__(
        self,
        absolute_path: Path,
        key: str,
        algo: Optional[AlgoSpec] = None,
    ):
        super().__init__(absolute_path)
        self.__key = key
        self.__algo = algo

    def open_r(self) -> EncryptedFileReader:
        return EncryptedFileReader(self._path, key=self.__key, algo=self.__algo)

    def open_w(self) -> EncryptedFileWriter:
        return EncryptedFileWriter(self._path, key=self.__key, algo=self.__algo)


class TokensStorageKeyring(TokensStoragePathBase):
    def __init__(
        self,
        absolute_path: Path,
        service: str,
        algo: Optional[AlgoSpec] = None,
    ):
        super().__init__()
        self.__absolute_path = absolute_path
        self.__service_name = service
        self.__algo = algo

    def _get_path_like(self) -> PathBase:
        return EncryptedFilePath(
            absolute_path=self.__absolute_path, key=self.__get_key(), algo=self.__algo
        )

    def __get_sanitized_path(self):
        return str(self.__absolute_path).replace("/", "_")

    def __get_key(self) -> str:
        key = keyring.get_password(
            service_name=self.__service_name, username=self.__get_sanitized_path()
        )
        if key is None:
            key = self.__generate_key()
        return key

    def __generate_key(self) -> str:
        key = generate_key()
        keyring.set_password(
            service_name=self.__service_name,
            username=self.__get_sanitized_path(),
            password=key,
        )
        return key

    async def _reset(self) -> None:
        self.__generate_key()
        self._get_path_like().ensure_exists()
