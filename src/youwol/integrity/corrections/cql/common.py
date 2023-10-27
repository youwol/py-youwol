# standard library
from abc import ABC, abstractmethod

# relative
from ...services.cql import CqlSession


class Correction(ABC):
    @abstractmethod
    def apply(self, session: CqlSession) -> None:
        pass
