from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.shared.errors import EmailUnavailable


class EmailPort(Protocol):
    def send_password_reset(self, to: str, url: str) -> None: ...


class DisabledEmail:
    def send_password_reset(self, to: str, url: str) -> None:
        raise EmailUnavailable()


@dataclass(frozen=True)
class ObjectInfo:
    size_bytes: int
    media_type: str
    etag: str


@dataclass(frozen=True)
class PresignedPost:
    url: str
    fields: dict[str, str]
    expires_at: datetime


class StoragePort(Protocol):
    """Private objects only; raise StorageMissing/StorageInvalid/StorageUnavailable.

    presign_post binds exact key, content type and size, expiry <= 5 minutes.
    copy requires source ETag and a fresh destination key. Streams close on exit.
    Implementations must never convert dependency failures to successful responses.
    """

    def presign_post(
        self, bucket: str, key: str, media_type: str, size_bytes: int, expires_at: datetime
    ) -> PresignedPost: ...
    def head(self, bucket: str, key: str) -> ObjectInfo: ...
    def read_stream(self, bucket: str, key: str) -> AbstractContextManager[Iterator[bytes]]: ...
    def copy(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        source_etag: str,
    ) -> None: ...
    def delete(self, bucket: str, key: str) -> None: ...
