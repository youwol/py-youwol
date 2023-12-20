# third parties
from _typeshed import Incomplete

class Credentials:
    def __init__(
        self,
        access_key,
        secret_key,
        session_token: Incomplete | None = ...,
        expiration: Incomplete | None = ...,
    ) -> None: ...
    @property
    def access_key(self): ...
    @property
    def secret_key(self): ...
    @property
    def session_token(self): ...
    def is_expired(self): ...
