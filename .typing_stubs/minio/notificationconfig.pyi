# standard library
from abc import ABCMeta

# third parties
from _typeshed import Incomplete

# relative
from .xml import Element as Element
from .xml import SubElement as SubElement
from .xml import find as find
from .xml import findall as findall
from .xml import findtext as findtext

class FilterRule:
    __metaclass__ = ABCMeta
    def __init__(self, name, value) -> None: ...
    @property
    def name(self): ...
    @property
    def value(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class PrefixFilterRule(FilterRule):
    def __init__(self, value) -> None: ...

class SuffixFilterRule(FilterRule):
    def __init__(self, value) -> None: ...

class CommonConfig:
    __metaclass__ = ABCMeta
    def __init__(
        self, events, config_id, prefix_filter_rule, suffix_filter_rule
    ) -> None: ...
    @property
    def events(self): ...
    @property
    def config_id(self): ...
    @property
    def prefix_filter_rule(self): ...
    @property
    def suffix_filter_rule(self): ...
    @staticmethod
    def parsexml(element): ...
    def toxml(self, element): ...

class CloudFuncConfig(CommonConfig):
    def __init__(
        self,
        cloud_func,
        events,
        config_id: Incomplete | None = ...,
        prefix_filter_rule: Incomplete | None = ...,
        suffix_filter_rule: Incomplete | None = ...,
    ) -> None: ...
    @property
    def cloud_func(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class QueueConfig(CommonConfig):
    def __init__(
        self,
        queue,
        events,
        config_id: Incomplete | None = ...,
        prefix_filter_rule: Incomplete | None = ...,
        suffix_filter_rule: Incomplete | None = ...,
    ) -> None: ...
    @property
    def queue(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class TopicConfig(CommonConfig):
    def __init__(
        self,
        topic,
        events,
        config_id: Incomplete | None = ...,
        prefix_filter_rule: Incomplete | None = ...,
        suffix_filter_rule: Incomplete | None = ...,
    ) -> None: ...
    @property
    def topic(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...

class NotificationConfig:
    def __init__(
        self,
        cloud_func_config_list: Incomplete | None = ...,
        queue_config_list: Incomplete | None = ...,
        topic_config_list: Incomplete | None = ...,
    ) -> None: ...
    @property
    def cloud_func_config_list(self): ...
    @property
    def queue_config_list(self): ...
    @property
    def topic_config_list(self): ...
    @classmethod
    def fromxml(cls, element): ...
    def toxml(self, element): ...
