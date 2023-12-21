"""
This module encapsulates files encryption utilities.
"""

# relative
from .constantes import Algo
from .exceptions import FileEncryptionException
from .file_encryption import decrypt_from_file, encrypt_into_file, generate_key
