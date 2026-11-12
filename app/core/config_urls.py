from ipaddress import ip_address
from urllib.parse import urlsplit


def is_local_http_api(value: str | None) -> bool:
    if value is None:
        return False
    url = urlsplit(value)
    return url.scheme == "http" and url.hostname == "localhost"


def endpoint(value: str, *, local_http: bool = False, internal: bool = False) -> str:
    if any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Whitespace/control characters forbidden in origins")
    url = urlsplit(value)
    try:
        loopback = url.hostname == "localhost" or ip_address(url.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if (
        not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in ("", "/")
        or url.port == 0
    ):
        raise ValueError("Expected an origin without credentials, path or query")
    if url.scheme != "https" and not (
        url.scheme == "http" and (internal or local_http and loopback)
    ):
        raise ValueError("HTTPS required (explicit local loopback exception only)")
    return value.rstrip("/")
