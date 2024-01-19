# relative
from .commonconfig import COMPLIANCE as COMPLIANCE
from .commonconfig import GOVERNANCE as GOVERNANCE
from .time import from_iso8601utc as from_iso8601utc
from .time import to_iso8601utc as to_iso8601utc
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import findtext as findtext

class Retention:
    def __init__(self, mode, retain_until_date) -> None: ...
    @property
    def mode(self): ...
    @property
    def retain_until_date(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
