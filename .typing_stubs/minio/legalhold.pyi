from .xml import Element as Element, SubElement as SubElement, findtext as findtext

class LegalHold:
    def __init__(self, status: bool = ...) -> None: ...
    @property
    def status(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
