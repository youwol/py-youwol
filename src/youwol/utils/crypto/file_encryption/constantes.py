# standard library
from enum import Enum

KEY_SIZE = 16  # key size in bytes, so KEY_SIZE = 16 => 128 bits


ALGO_HEADER_LENGTH = 1


class Algo(Enum):
    """
    Available algorithms for file encryption.

    Enum entry value will be the first byte of the encrypted file, and identify the algorithm used.
    """

    NULL = 0x0A
    """
    A NULL cipher, an almost no-op encryption: encrypted data will be almost the same as plain data,
     except for the addition of a single new line character at the begin of the file.
    """

    SIV_256 = 0x01
    """
    AES-SIV (RFC 5297) with a key size of 256 bits : Synthetic Initialization Vector (SIV) mode
     for AES cipher, with a block size of 128 bits.
    """


default_algo: Algo = Algo.SIV_256
