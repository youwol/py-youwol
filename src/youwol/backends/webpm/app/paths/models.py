# third parties
from pydantic import BaseModel


class Origin(BaseModel):
    secure: bool
    hostname: str
    port: int

    @staticmethod
    def from_host(host: str):
        secure = False
        if host.startswith("https://"):
            secure = True
        elif not host.startswith("http://"):
            raise RuntimeError(f"Host '{host}' does not start with scheme")
        after_scheme_pos = 8 if secure else 7
        host_without_scheme = host[after_scheme_pos:]
        colon_pos = host_without_scheme.find(":")
        if colon_pos != -1:
            port_str = host_without_scheme[colon_pos + 1 :]
            if str(int(port_str)) != port_str:
                raise RuntimeError(f"Host '{host}' has invalid port {port_str}")
            port = int(port_str)
        else:
            port = 443 if secure else 80
            colon_pos = len(host_without_scheme)
        hostname = host_without_scheme[:colon_pos]
        return Origin(secure=secure, hostname=hostname, port=port)


class ClientConfig(BaseModel):
    id: str
    origin: Origin
    pathLoadingGraph: str
    pathResource: str
