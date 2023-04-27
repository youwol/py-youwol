from .commonconfig import COMPLIANCE as COMPLIANCE, ENABLED as ENABLED, GOVERNANCE as GOVERNANCE
from .xml import Element as Element, SubElement as SubElement, find as find, findtext as findtext

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
