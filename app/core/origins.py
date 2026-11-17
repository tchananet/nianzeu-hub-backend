import re
from urllib.parse import SplitResult, urlsplit

CORS_METHODS = ("GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS")
CORS_HEADERS = ("Content-Type", "X-CSRF-Token", "X-Auth-Intent")
CORS_EXPOSE_HEADERS = ("X-Request-ID", "Retry-After", "Location")
LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.ASCII)


def normalize_origin(value: str) -> str:
    if not value or not value.isascii() or any(c.isspace() or ord(c) < 33 for c in value):
        raise ValueError("Invalid origin")
    if any(c in value for c in ("%", "\\", "?", "#", "\x7f")):
        raise ValueError("Invalid origin")
    url = urlsplit(value)
    host = url.hostname or ""
    if (url.scheme not in {"http", "https"} or url.path or url.query or url.fragment
            or "@" in url.netloc or not host or len(host) > 253
            or any(LABEL.fullmatch(label) is None for label in host.split("."))):
        raise ValueError("Invalid origin")
    if ":" in url.netloc:
        raw_port = url.netloc.rsplit(":", 1)[1]
        if not raw_port.isascii() or not raw_port.isdecimal():
            raise ValueError("Invalid origin port")
    port = url.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid origin port")
    suffix = "" if port is None or port == {"http": 80, "https": 443}[url.scheme] else f":{port}"
    return f"{url.scheme}://{host}{suffix}"


def local_browser_origin(url: SplitResult, environment: str) -> bool:
    """Development convenience: any localhost port, never outside local/test."""
    return (environment in {"local", "test"} and url.scheme == "http"
            and url.hostname == "localhost")


WILDCARD = "https://*."


def wildcard_suffix(pattern: str) -> str | None:
    """`https://*.example.com` -> `example.com`; anything else -> None."""
    if not pattern.startswith(WILDCARD):
        return None
    return pattern[len(WILDCARD):]


def matches(pattern: str, candidate: str) -> bool:
    suffix = wildcard_suffix(pattern)
    if suffix is None:
        return pattern == candidate
    url = urlsplit(candidate)
    host = url.hostname or ""
    # endswith on a dotted suffix, so example.com.evil.test can never match.
    return url.scheme == "https" and url.port in {None, 443} and host.endswith(f".{suffix}")


def is_allowed_origin(
    value: str, environment: str, configured: tuple[str, ...] | None = None
) -> bool:
    """Only the configured origins are trusted. No domain is trusted implicitly.

    `configured` holds the already-normalised entries of ``APP_FRONTEND_ORIGIN``.
    Passing None or an empty tuple trusts nothing, so a caller that forgets to supply
    them fails closed rather than open.
    """
    try:
        candidate = normalize_origin(value)
    except ValueError:
        return False
    if local_browser_origin(urlsplit(candidate), environment):
        return True
    return any(matches(pattern, candidate) for pattern in configured or ())


def usable_origin(value: str, environment: str) -> str:
    """Validates one configured entry; returns it normalised.

    A `https://*.example.com` wildcard is accepted, but never with fewer than two
    labels after the star: `https://*.app` would hand trust to an entire TLD.
    """
    value = value.strip()  # a list written as "a, b" keeps the separating space
    suffix = wildcard_suffix(value.lower())
    if suffix is not None:
        host = urlsplit(f"https://{suffix}").hostname or ""
        if host != suffix or host.count(".") < 1 or any(
            LABEL.fullmatch(label) is None for label in host.split(".")
        ):
            raise ValueError("A wildcard origin needs a host of at least two labels")
        return f"{WILDCARD}{host}"
    candidate = normalize_origin(value)
    url = urlsplit(candidate)
    if url.scheme == "https" and url.port in {None, 443}:
        return candidate
    if local_browser_origin(url, environment):
        return candidate
    raise ValueError("Frontend origin must be HTTPS; http://localhost only in local/test")
