import hashlib
import hmac
import secrets
from datetime import UTC, datetime
from ipaddress import ip_address
from typing import Protocol


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class SecretGenerator(Protocol):
    def __call__(self) -> str: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


def quota_key(secret: str, identity: str) -> str:
    return hmac.new(secret.encode(), identity.encode(), hashlib.sha256).hexdigest()


def ip_quota_key(secret: str, address: str) -> str:
    parsed = ip_address(address)
    normalized = getattr(parsed, "ipv4_mapped", None) or parsed
    return quota_key(secret, str(normalized))
