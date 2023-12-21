"""
This module gathers the service  ̀assets-gateway`, it is served from the path `/api/assets-gateway`.
"""
# relative
from .configurations import Configuration, Constants, Dependencies
from .root_paths import router
from .router import get_router
