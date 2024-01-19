# third parties
from _typeshed import Incomplete

# relative
from .commonconfig import DISABLED as DISABLED
from .commonconfig import ENABLED as ENABLED
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import findtext as findtext

OFF: str
SUSPENDED: str

class VersioningConfig:
    def __init__(
        self, status: Incomplete | None = ..., mfa_delete: Incomplete | None = ...
    ) -> None: ...
    @property
    def status(self): ...
    @property
    def mfa_delete(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
