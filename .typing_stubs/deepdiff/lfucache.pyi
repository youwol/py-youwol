# third parties
from _typeshed import Incomplete
from deepdiff.helper import dict_ as dict_
from deepdiff.helper import not_found as not_found

class CacheNode:
    key: Incomplete
    content: Incomplete
    freq_node: Incomplete
    pre: Incomplete
    nxt: Incomplete
    def __init__(self, key, report_type, value, freq_node, pre, nxt) -> None: ...
    def free_myself(self) -> None: ...

class FreqNode:
    freq: Incomplete
    pre: Incomplete
    nxt: Incomplete
    cache_head: Incomplete
    cache_tail: Incomplete
    def __init__(self, freq, pre, nxt) -> None: ...
    def count_caches(self): ...
    def remove(self): ...
    def pop_head_cache(self): ...
    def append_cache_to_tail(self, cache_node) -> None: ...
    def insert_after_me(self, freq_node) -> None: ...
    def insert_before_me(self, freq_node) -> None: ...

class LFUCache:
    cache: Incomplete
    capacity: Incomplete
    freq_link_head: Incomplete
    lock: Incomplete
    def __init__(self, capacity) -> None: ...
    def get(self, key): ...
    def set(
        self, key, report_type: Incomplete | None = ..., value: Incomplete | None = ...
    ) -> None: ...
    def __contains__(self, key) -> bool: ...
    def move_forward(self, cache_node, freq_node) -> None: ...
    def dump_cache(self) -> None: ...
    def create_cache_node(self, key, report_type, value) -> None: ...
    def get_sorted_cache_keys(self): ...
    def get_average_frequency(self): ...

class DummyLFU:
    def __init__(self, *args, **kwargs) -> None: ...
    set = __init__
    get = __init__
    def __contains__(self, key) -> bool: ...
