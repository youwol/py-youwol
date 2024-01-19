# standard library
from abc import ABCMeta

# third parties
from _typeshed import Incomplete

# relative
from .commonconfig import DISABLED as DISABLED
from .commonconfig import BaseRule as BaseRule
from .commonconfig import check_status as check_status
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import find as find
from .xml import findall as findall
from .xml import findtext as findtext

class Status:
    __metaclass__ = ABCMeta
    def __init__(self, status) -> None: ...
    @property
    def status(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class SseKmsEncryptedObjects(Status): ...

class SourceSelectionCriteria:
    def __init__(self, sse_kms_encrypted_objects: Incomplete | None = ...) -> None: ...
    @property
    def sse_kms_encrypted_objects(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class ExistingObjectReplication(Status): ...

class DeleteMarkerReplication(Status):
    def __init__(self, status=...) -> None: ...

class ReplicationTimeValue:
    __metaclass__ = ABCMeta
    def __init__(self, minutes: int = ...) -> None: ...
    @property
    def minutes(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class Time(ReplicationTimeValue): ...

class ReplicationTime:
    def __init__(self, time, status) -> None: ...
    @property
    def time(self): ...
    @property
    def status(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class EventThreshold(ReplicationTimeValue): ...

class Metrics:
    def __init__(self, event_threshold, status) -> None: ...
    @property
    def event_threshold(self): ...
    @property
    def status(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class EncryptionConfig:
    def __init__(self, replica_kms_key_id: Incomplete | None = ...) -> None: ...
    @property
    def replica_kms_key_id(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class AccessControlTranslation:
    def __init__(self, owner: str = ...) -> None: ...
    @property
    def owner(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class Destination:
    def __init__(
        self,
        bucket_arn,
        access_control_translation: Incomplete | None = ...,
        account: Incomplete | None = ...,
        encryption_config: Incomplete | None = ...,
        metrics: Incomplete | None = ...,
        replication_time: Incomplete | None = ...,
        storage_class: Incomplete | None = ...,
    ) -> None: ...
    @property
    def bucket_arn(self): ...
    @property
    def access_control_translation(self): ...
    @property
    def account(self): ...
    @property
    def encryption_config(self): ...
    @property
    def metrics(self): ...
    @property
    def replication_time(self): ...
    @property
    def storage_class(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class Rule(BaseRule):
    def __init__(
        self,
        destination,
        status,
        delete_marker_replication: Incomplete | None = ...,
        existing_object_replication: Incomplete | None = ...,
        rule_filter: Incomplete | None = ...,
        rule_id: Incomplete | None = ...,
        prefix: Incomplete | None = ...,
        priority: Incomplete | None = ...,
        source_selection_criteria: Incomplete | None = ...,
    ) -> None: ...
    @property
    def destination(self): ...
    @property
    def status(self): ...
    @property
    def delete_marker_replication(self): ...
    @property
    def existing_object_replication(self): ...
    @property
    def prefix(self): ...
    @property
    def priority(self): ...
    @property
    def source_selection_criteria(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class ReplicationConfig:
    def __init__(self, role, rules) -> None: ...
    @property
    def role(self): ...
    @property
    def rules(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
