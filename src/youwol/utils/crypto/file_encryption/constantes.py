# standard library
from enum import Enum

# typing
from typing import Optional

KEY_SIZE = 16  # key size in bytes, so KEY_SIZE = 16 => 128 bits


ALGO_HEADER_LENGTH = 1


class Algo(Enum):
    NULL = 0x0A  # A single new line '\n'
    SIV_256 = 0x01


default_algo: Algo = Algo.SIV_256


def algo_to_byte(algo: Algo) -> bytes:
    return algo.value.to_bytes(ALGO_HEADER_LENGTH, byteorder="little")


def algo_from_byte(byte: bytes) -> Optional[Algo]:
    if len(byte) != ALGO_HEADER_LENGTH:
        raise ValueError(f"Expected {ALGO_HEADER_LENGTH} byte(s)")

    for candidate in Algo:
        if algo_to_byte(candidate) == byte:
            return candidate

    return None
