"""
Gathers the endpoints of the assets-backend service gathered by topic.
"""

# relative
from .access import router as router_access
from .assets import router as router_assets
from .files import router as router_files
from .images import router as router_images
from .permissions import router as router_permissions
from .raw import router as router_raw
