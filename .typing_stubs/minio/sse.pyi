# standard library
import abc

from abc import ABCMeta, abstractmethod

class Sse(metaclass=abc.ABCMeta):
    __metaclass__ = ABCMeta
    @abstractmethod
    def headers(self): ...
    def tls_required(self): ...
    def copy_headers(self): ...

class SseCustomerKey(Sse):
    def __init__(self, key) -> None: ...
    def headers(self): ...
    def copy_headers(self): ...

class SseKMS(Sse):
    def __init__(self, key, context) -> None: ...
    def headers(self): ...

class SseS3(Sse):
    def headers(self): ...
    def tls_required(self): ...
