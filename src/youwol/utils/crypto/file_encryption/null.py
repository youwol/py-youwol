# typing
from typing import BinaryIO

# relative
from .constantes import ALGO_HEADER_LENGTH, Algo, algo_to_byte
from .exceptions import BadKeyValue

NULL_KEY = "password"


class KeyValueNotNullKey(BadKeyValue):
    def __init__(self):
        super().__init__(
            algo=Algo.NULL, reason=f"key is not hardcoded value '{NULL_KEY}'"
        )


def null_generate_key():
    return NULL_KEY


def null_encrypt_into_file(fp: BinaryIO, data: str, key: str) -> None:
    if key != NULL_KEY:
        raise KeyValueNotNullKey()
    fp.write(algo_to_byte(Algo.NULL))
    fp.write(data.encode(encoding="utf-8"))


def null_decrypt_from_file(fp: BinaryIO, key: str):
    if key != NULL_KEY:
        raise KeyValueNotNullKey()
    fp.seek(ALGO_HEADER_LENGTH)
    return fp.read().decode("utf-8")
