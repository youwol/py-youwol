# standard library
import json
import threading

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from json import JSONDecodeError
from pathlib import Path

# typing
from typing import Dict, Optional

# Youwol utilities
from youwol.utils.clients.oidc.tokens_manager import TokensData, TokensStorage

atomic_access = threading.Lock()


class TokensStoragePathBaseException(RuntimeError):
    pass


class ReaderBase(AbstractContextManager):
    @abstractmethod
    def read(self, n: int = -1) -> str:
        pass

    @abstractmethod
    def _close(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()


class WriterBase(AbstractContextManager):
    @abstractmethod
    def write(self, data: str) -> int:
        pass

    @abstractmethod
    def _exit_without_exception(self):
        pass

    @abstractmethod
    def _close(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._exit_without_exception()
        self._close()


class PathBase(ABC):
    def __init__(self, absolute_path: Path):
        self._path = absolute_path

    @abstractmethod
    def open_r(self) -> ReaderBase:
        pass

    @abstractmethod
    def open_w(self) -> WriterBase:
        pass

    def ensure_exists(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)


class TokensStoragePathBase(TokensStorage, ABC):
    def __init__(self):
        self.__tokens_data: Dict[str, TokensData] = {}
        self.__session_ids: Dict[str, str] = {}

    @abstractmethod
    def _get_path_like(self) -> PathBase:
        pass

    @abstractmethod
    async def _reset(self) -> None:
        pass

    async def get(self, tokens_id: str) -> Optional[TokensData]:
        with atomic_access:
            if tokens_id not in self.__tokens_data:
                return None
            return self.__tokens_data[tokens_id]

    async def delete(self, tokens_id: str, session_id: str) -> None:
        with atomic_access:
            if tokens_id in self.__tokens_data:
                del self.__tokens_data[tokens_id]
            if session_id in self.__session_ids:
                del self.__session_ids[session_id]
            await self.__save_data()

    async def get_by_sid(
        self, session_id: str
    ) -> (Optional[str], Optional[TokensData]):
        with atomic_access:
            if session_id not in self.__session_ids:
                return None, None
            tokens_id = self.__session_ids[session_id]
            if tokens_id not in self.__tokens_data:
                return tokens_id, None
            return self.__tokens_data[tokens_id]

    async def store(self, tokens_id: str, data: TokensData) -> None:
        with atomic_access:
            self.__tokens_data[tokens_id] = data
            self.__session_ids[data.session_state] = tokens_id
            await self.__save_data()

    async def load_data(self):
        try:
            await self.__try_load_data()
        except TokensStoragePathBaseException as e:
            print(f"Reset Tokens storage : {e}")
            await self.__reset()
            await self.__try_load_data()

    async def __try_load_data(self):
        with self._get_path_like().open_r() as fp:
            try:
                data = json.load(fp)
            except JSONDecodeError as e:
                raise TokensStoragePathBaseException(e)
            if "tokens_data" in data:
                self.__tokens_data = {
                    tokens_id: TokensData(**data["tokens_data"][tokens_id])
                    for tokens_id in data["tokens_data"]
                }
            else:
                self.__tokens_data = {}
            if "session_ids" in data:
                self.__session_ids = {
                    session_id: data["session_ids"][session_id]
                    for session_id in data["session_ids"]
                }
            else:
                self.__session_ids = {}

    async def __save_data(self):
        try:
            await self.__try_save_data()
        except TokensStoragePathBaseException as e:
            print(f"Reset Tokens storage: {e}")
            await self.__reset()
            await self.__try_save_data()

    async def __try_save_data(self):
        data = {
            "tokens_data": {
                tokens_id: tokens_data.__dict__
                for tokens_id, tokens_data in self.__tokens_data.items()
            },
            "session_ids": self.__session_ids,
        }
        with self._get_path_like().open_w() as fp:
            json.dump(data, fp)

    async def __reset(self) -> None:
        await self._reset()
        with self._get_path_like().open_w() as fp:
            fp.write("{}")
