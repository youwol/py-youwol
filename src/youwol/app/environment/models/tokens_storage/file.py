# standard library
from pathlib import Path

# typing
from typing import TextIO

# relative
from .path_base import PathBase, TokensStoragePathBase, TokensStoragePathBaseException


class FilePath(PathBase):
    def open_w(self) -> TextIO:
        return self._path.open(mode="w")

    def open_r(self) -> TextIO:
        try:
            return self._path.open(mode="r")
        except FileNotFoundError as e:
            raise TokensStoragePathBaseException(e)


class TokensStorageFile(TokensStoragePathBase):
    def __init__(self, absolute_path: Path):
        super().__init__()
        self.__path = FilePath(absolute_path=absolute_path)

    def _get_path_like(self) -> PathBase:
        return self.__path

    async def _reset(self) -> None:
        self.__path.ensure_exists()
