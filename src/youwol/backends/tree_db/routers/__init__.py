"""
Gathers tree_db backend end-points by topics.
"""

# relative
from .drives import router as router_drives
from .entities import router as router_entities
from .folders import router as router_folders
from .groups import router as router_groups
from .items import router as router_items
