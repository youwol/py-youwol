# standard library
import base64
import struct

# typing
from typing import BinaryIO

# third parties
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# relative
from .constantes import KEY_SIZE, Algo, algo_from_byte, algo_to_byte
from .exceptions import BadAlgo, BadKeyLength, BadKeyValue, FileDecryptionFailed

SIV_KEY_SIZE = 2 * KEY_SIZE

SIV_256_PACK_FORMAT = "cIII"


class KeyB64DecodingFailure(BadKeyValue):
    def __init__(self, e: ValueError):
        super().__init__(
            algo=Algo.SIV_256, reason=f"base64 decoding failed (error is '{e}')"
        )


class SivBadKeyLength(BadKeyLength):
    def __init__(self, key: bytes):
        super().__init__(algo=Algo.SIV_256, expected=SIV_KEY_SIZE, actual=len(key))


def siv_256_generate_key() -> str:
    return base64.b64encode(get_random_bytes(SIV_KEY_SIZE)).decode(encoding="utf-8")


def siv_256_encrypt_into_file(fp: BinaryIO, data: str, key: str, debug=False) -> None:
    try:
        key = base64.b64decode(key)
    except ValueError as e:
        raise KeyB64DecodingFailure(e)
    if len(key) != SIV_KEY_SIZE:
        raise SivBadKeyLength(key)
    data_bytes = data.encode(encoding="utf-8")
    siv_256_header_length = struct.calcsize(SIV_256_PACK_FORMAT)
    siv_256_nonce_length = 16
    siv_256_data_length = len(data_bytes)
    if debug:
        print(
            f"header: {siv_256_header_length}, nonce: {siv_256_nonce_length}, data: {siv_256_data_length}, "
            f"algo: {algo_to_byte(Algo.SIV_256)}"
        )

    header = struct.pack(
        SIV_256_PACK_FORMAT,
        algo_to_byte(Algo.SIV_256),
        siv_256_header_length,
        siv_256_nonce_length,
        siv_256_data_length,
    )
    nonce = get_random_bytes(siv_256_nonce_length)
    cipher = AES.new(key, AES.MODE_SIV, nonce=nonce)
    cipher.update(header)
    ciphertext, tag = cipher.encrypt_and_digest(data_bytes)
    if debug:
        print(f"h:{header}, nonce:{nonce}, ciphertext:{ciphertext}, tag:{tag}")
    fp.write(header)
    fp.write(nonce)
    fp.write(ciphertext)
    fp.write(tag)


def siv_256_decrypt_from_file(fp: BinaryIO, key: str, debug=False) -> str:
    try:
        key = base64.b64decode(key)
    except ValueError as e:
        raise KeyB64DecodingFailure(e)
    if len(key) != SIV_KEY_SIZE:
        raise SivBadKeyLength(key)
    header = fp.read(struct.calcsize(SIV_256_PACK_FORMAT))
    algo_byte, header_length, nonce_length, data_length = struct.unpack(
        SIV_256_PACK_FORMAT, header
    )
    if debug:
        print(
            f"algo:{algo_byte}, header:{header_length}, nonce:{nonce_length}, data:{data_length}"
        )
    if algo_from_byte(algo_byte) != Algo.SIV_256:
        raise BadAlgo(expected=Algo.SIV_256, actual=algo_from_byte(algo_byte))
    nonce = fp.read(nonce_length)
    ciphertext = fp.read(data_length)
    tag = fp.read()
    if debug:
        print(f"header:{header}, nonce:{nonce}, ciphertext:{ciphertext}, tag:{tag}")

    cipher = AES.new(key, AES.MODE_SIV, nonce=nonce)
    cipher.update(header)
    try:
        data = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as e:
        msg = str(e)
        if msg == "MAC check failed":
            raise FileDecryptionFailed(algo=Algo.SIV_256, reason=msg)
        raise e
    if debug:
        print(f"data:{data}")

    return data.decode(encoding="utf-8")
