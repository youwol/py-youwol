# relative
from .constantes import ALGO_HEADER_LENGTH, Algo
from .exceptions import UnknownAlgo


def algo_to_byte(algo: Algo) -> bytes:
    return algo.value.to_bytes(ALGO_HEADER_LENGTH, byteorder="little")


def algo_from_byte(byte: bytes) -> Algo:
    if len(byte) != ALGO_HEADER_LENGTH:
        raise ValueError(f"Expected {ALGO_HEADER_LENGTH} byte(s)")

    for candidate in Algo:
        if algo_to_byte(candidate) == byte:
            return candidate

    raise UnknownAlgo(f"Byte(s) '{byte.hex(' ')}' does not match any algo")
