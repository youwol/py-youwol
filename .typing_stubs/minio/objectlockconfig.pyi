# relative
from .commonconfig import COMPLIANCE as COMPLIANCE
from .commonconfig import ENABLED as ENABLED
from .commonconfig import GOVERNANCE as GOVERNANCE
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import find as find
from .xml import findtext as findtext

DAYS: str
YEARS: str

class ObjectLockConfig:
    def __init__(self, mode, duration, duration_unit) -> None: ...
    @property
    def mode(self): ...
    @property
    def duration(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
