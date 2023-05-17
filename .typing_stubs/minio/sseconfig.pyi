from .xml import Element as Element, SubElement as SubElement, find as find, findtext as findtext
from _typeshed import Incomplete
from abc import ABCMeta

AES256: str
AWS_KMS: str

class Rule:
    __metaclass__ = ABCMeta
    def __init__(self, sse_algorithm, kms_master_key_id: Incomplete | None = ...) -> None: ...
    @property
    def sse_algorithm(self): ...
    @property
    def kms_master_key_id(self): ...
    @classmethod
    def new_sse_s3_rule(cls): ...
    @classmethod
    def new_sse_kms_rule(cls, kms_master_key_id: Incomplete | None = ...): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class SSEConfig:
    def __init__(self, rule) -> None: ...
    @property
    def rule(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
