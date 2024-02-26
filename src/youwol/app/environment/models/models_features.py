# third parties
from pydantic import BaseModel


class Features(BaseModel):
    """Application Features"""

    configDependantBrowserCaching: bool = False
    """ Tie the browser caching to the configuration """
