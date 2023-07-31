# standard library
import datetime
import json
import threading

from json import JSONDecodeError
from pathlib import Path

# typing
from typing import Dict, Optional

# third parties
import keyring

# Youwol utilities
from youwol.utils import TokensData
from youwol.utils.clients.oidc.tokens_manager import TokensStorage

atomic_access = threading.Lock()


class TokensStorageFile(TokensStorage):
    def __init__(self, absolute_path: Path):
        self.__path = absolute_path
        self.__tokens_data: Dict[str, TokensData] = {}
        self.__session_ids: Dict[str, str] = {}

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
        if not self.__path.exists():
            await self.__write_empty()
        with self.__path.open(mode="r") as fp:
            try:
                data = json.load(fp)
            except JSONDecodeError:
                await self.__write_empty()
                data = {}
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
        with self.__path.open(mode="w") as fp:
            data = {
                "tokens_data": {
                    tokens_id: tokens_data.__dict__
                    for tokens_id, tokens_data in self.__tokens_data.items()
                },
                "session_ids": self.__session_ids,
            }
            json.dump(data, fp)

    async def __write_empty(self):
        with self.__path.open(mode="w") as fp:
            fp.write("{}")


class TokensStorageKeyring(TokensStorage):
    def __init__(self, service: str):
        self.__service = service

    async def get(self, tokens_id: str) -> Optional[TokensData]:
        data = self.__get_pass(tokens_id)
        if data is None:
            return None
        result = TokensData(**json.loads(data))
        if result.refresh_expires_at < datetime.datetime.now().timestamp():
            await self.delete(tokens_id, result.session_state)
            return None
        return result

    async def delete(self, tokens_id: str, session_id: str) -> None:
        if self.__get_pass(tokens_id) is not None:
            self.__set_pass(tokens_id)
        if self.__get_pass(session_id) is not None:
            self.__set_pass(session_id)

    async def get_by_sid(
        self, session_id: str
    ) -> (Optional[str], Optional[TokensData]):
        tokens_id = self.__get_pass(session_id)
        if tokens_id is None:
            return None, None
        return tokens_id, await self.get(tokens_id)

    async def store(self, tokens_id: str, data: TokensData) -> None:
        session_id = data.session_state
        self.__set_pass(tokens_id, json.dumps(data.__dict__))
        self.__set_pass(session_id, tokens_id)

    def __get_pass(self, key: str) -> Optional[str]:
        return keyring.get_password(self.__service, key)

    def __set_pass(self, key: str, content: Optional[str] = None):
        if content:
            keyring.set_password(self.__service, key, content)
        else:
            keyring.delete_password(self.__service, key)
