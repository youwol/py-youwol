# standard library
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class Features:
    config_dependant_browser_caching: bool = False
