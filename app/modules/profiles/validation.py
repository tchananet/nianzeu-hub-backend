import re
from datetime import date
from urllib.parse import urlsplit
from uuid import UUID


def calendar_date(value: object) -> date:
    if isinstance(value, date) and type(value) is date:
        return value
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("ISO calendar date required")
    return date.fromisoformat(value)


def uuid_value(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str) or re.fullmatch(
        r"[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value,
    ) is None:
        raise ValueError("UUID required")
    return UUID(value)


def https_link(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or "@" in parsed.netloc
            or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value):
        raise ValueError("HTTPS link without credentials required")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid link port")
    return value
