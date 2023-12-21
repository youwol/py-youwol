# third parties
from starlette.middleware.cors import CORSMiddleware

# relative
from .cache_vary import VaryHeaderMiddleware
from .coep import COEPHeaderMiddleware

__all__ = ["COEPHeaderMiddleware", "CORSMiddleware", "VaryHeaderMiddleware"]
