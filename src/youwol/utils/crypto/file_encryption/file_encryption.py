# standard library
from pathlib import Path

# typing
from typing import BinaryIO, Callable, Optional

# relative
from .constantes import ALGO_HEADER_LENGTH, Algo, default_algo
from .exceptions import AlgoOperationMissing, BadAlgo, FileEmpty, FileNotFound
from .null import null_decrypt_from_file, null_encrypt_into_file, null_generate_key
from .siv_256 import (
    siv_256_decrypt_from_file,
    siv_256_encrypt_into_file,
    siv_256_generate_key,
)
from .utils import algo_from_byte, algo_to_byte


def encrypt_into_file(
    data: str, path: Path, key: str, algo: Algo = default_algo
) -> None:
    with path.open(mode="wb") as fp:
        fp.write(algo_to_byte(algo))
        fp.seek(0)
        fn = encryption.get(algo)
        if fn is None:
            raise AlgoOperationMissing(algo=algo, operation="encrypt_file")
        fn(fp, data, key)


def decrypt_from_file(
    path: Path, key: str, expected_algo: Optional[Algo] = default_algo
) -> str:
    if not path.exists():
        raise FileNotFound(path)
    if path.stat().st_size == 0:
        raise FileEmpty(path)
    with path.open(mode="rb") as fp:
        byte = fp.read(ALGO_HEADER_LENGTH)
        algo = algo_from_byte(byte)
        if expected_algo is not None and algo != expected_algo:
            raise BadAlgo(expected=expected_algo, actual=algo)
        fp.seek(0)
        fn = decryption.get(algo)
        if fn is None:
            raise AlgoOperationMissing(algo=algo, operation="decrypt_file")
        return fn(fp, key)


def generate_key(algo: Algo = default_algo) -> str:
    fn = key_generation.get(algo)
    if fn is None:
        raise AlgoOperationMissing(algo=algo, operation="generate_key")
    return fn()


encryption: dict[Algo, Callable[[BinaryIO, str, str], None]] = {
    Algo.SIV_256: siv_256_encrypt_into_file,
    Algo.NULL: null_encrypt_into_file,
}


decryption: dict[Algo, Callable[[BinaryIO, str], str]] = {
    Algo.SIV_256: siv_256_decrypt_from_file,
    Algo.NULL: null_decrypt_from_file,
}

key_generation = {Algo.NULL: null_generate_key, Algo.SIV_256: siv_256_generate_key}
