# third parties
from starlette.requests import Request

VALUE_WHEN_REQUEST_HAS_NO_CLIENT = "__STARLETTE_REQUEST_HAS_NO_CLIENT__"

VALUE_WHEN_REQUEST_HAS_NO_USER_AGENT_HEADER = "__NO_HEADER_USER_AGENT__"


def get_real_client_ip(req: Request) -> str:
    """Get the client real IP, including behind proxy

    Return the IP or the constant VALUE_WHEN_REQUEST_HAS_NO_CLIENT"""
    return (
        req.client.host if req.client is not None else VALUE_WHEN_REQUEST_HAS_NO_CLIENT
    )
