# standard library
from enum import Enum

KEY_SIZE = 16  # key size in bytes, so KEY_SIZE = 16 => 128 bits


ALGO_HEADER_LENGTH = 1


class Algo(Enum):
    NULL = 0x0A  # A single new line '\n'
    SIV_256 = 0x01


default_algo: Algo = Algo.SIV_256
