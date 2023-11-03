# standard library
from pathlib import Path

# relative
from .constantes import Algo


class FileEncryptionException(Exception):
    pass


class UnknownAlgo(FileEncryptionException):
    def __init__(self, reason: str):
        super().__init__(f"Cannot determine algo because {reason}")


class FileNotFound(FileEncryptionException):
    def __init__(self, path: Path):
        super().__init__(f"File not found at '{path.absolute()}'")


class FileEmpty(FileEncryptionException):
    def __init__(self, path: Path):
        super().__init__(f"File at '{path.absolute()}' is empty")


class FileDecryptionFailed(FileEncryptionException):
    def __init__(self, algo: Algo, reason: str):
        super().__init__(
            f"File decryption with algo '{algo.name}' failed because {reason}"
        )


class BadKeyLength(FileEncryptionException):
    def __init__(self, algo: Algo, expected: int, actual: int):
        super().__init__(
            f"Expected key length for algo '{algo.name}' is {expected}, got key of length {actual}"
        )


class BadKeyValue(FileEncryptionException):
    def __init__(self, algo: Algo, reason: str):
        super().__init__(
            f"Key value for algo '{algo.name}' is invalid because {reason}"
        )


class BadAlgo(FileEncryptionException):
    def __init__(self, expected: Algo, actual: Algo):
        super().__init__(f"Expected algo {expected}, found {actual}")


class AlgoOperationMissing(FileEncryptionException):
    def __init__(self, algo: Algo, operation: str):
        super().__init__(
            f"No implementation for operation '{operation}' and algo '{algo.name}'"
        )
