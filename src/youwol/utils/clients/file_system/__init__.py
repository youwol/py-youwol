"""
This module gathers file-system interface & implementation definitions.
"""

# relative
from .interfaces import *
from .local_file_system import *
from .minio_file_system import *

# we do not want to import minio_file_system here because minio is optional
