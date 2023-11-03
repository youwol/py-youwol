# standard library
from pathlib import Path

# typing
from typing import Optional

# relative
from .constantes import (
    ALGO_HEADER_LENGTH,
    Algo,
    algo_from_byte,
    algo_to_byte,
    default_algo,
)
from .exceptions import (
    AlgoOperationMissing,
    BadAlgo,
    FileEmpty,
    FileNotFound,
    UnknownAlgo,
)
from .null import null_decrypt_from_file, null_encrypt_into_file, null_generate_key
from .siv_256 import (
    siv_256_decrypt_from_file,
    siv_256_encrypt_into_file,
    siv_256_generate_key,
)


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
        if algo is None:
            raise UnknownAlgo(f"Byte(s) '{byte.hex(' ')}' does not match any algo")
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


encryption = {
    Algo.SIV_256: siv_256_encrypt_into_file,
    Algo.NULL: null_encrypt_into_file,
}


decryption = {
    Algo.SIV_256: siv_256_decrypt_from_file,
    Algo.NULL: null_decrypt_from_file,
}

key_generation = {Algo.NULL: null_generate_key, Algo.SIV_256: siv_256_generate_key}
