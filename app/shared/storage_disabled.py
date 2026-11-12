from collections.abc import Iterator
from contextlib import AbstractContextManager
from datetime import datetime

from app.shared.errors import StorageUnavailable
from app.shared.ports import ObjectInfo, PresignedPost


class DisabledStorage:
    """Explicit unavailable fallback until an actual private storage adapter is wired."""

    def presign_post(
        self, bucket: str, key: str, media_type: str, size_bytes: int, expires_at: datetime
    ) -> PresignedPost:
        raise StorageUnavailable()

    def head(self, bucket: str, key: str) -> ObjectInfo:
        raise StorageUnavailable()

    def read_stream(self, bucket: str, key: str) -> AbstractContextManager[Iterator[bytes]]:
        raise StorageUnavailable()

    def copy(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        source_etag: str,
    ) -> None:
        raise StorageUnavailable()

    def delete(self, bucket: str, key: str) -> None:
        raise StorageUnavailable()
