import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.shared.errors import StorageInvalid, StorageMissing, StorageUnavailable
from app.shared.ports import ObjectInfo, PresignedPost


@dataclass
class StoredObject:
    data: bytes
    media_type: str
    modified: datetime


@dataclass
class FakeStorage:
    """In-memory private buckets; ETag is an MD5 digest, never a SHA-256 hash."""

    buckets: dict[str, dict[str, StoredObject]] = field(default_factory=dict)
    unavailable: bool = False
    signed: list[tuple[str, str, str, int]] = field(default_factory=list)

    def put(
        self,
        bucket: str,
        key: str,
        data: bytes,
        media_type: str = "application/octet-stream",
        modified: datetime | None = None,
    ) -> None:
        when = modified or datetime.now(UTC)
        self.buckets.setdefault(bucket, {})[key] = StoredObject(data, media_type, when)

    def object_at(self, bucket: str, key: str) -> StoredObject:
        if self.unavailable:
            raise StorageUnavailable()
        found = self.buckets.get(bucket, {}).get(key)
        if found is None:
            raise StorageMissing()
        return found

    def presign_post(
        self, bucket: str, key: str, media_type: str, size_bytes: int, expires_at: datetime
    ) -> PresignedPost:
        if self.unavailable:
            raise StorageUnavailable()
        self.signed.append((bucket, key, media_type, size_bytes))
        return PresignedPost(
            f"https://files.test/{bucket}",
            {
                "key": key,
                "Content-Type": media_type,
                "content-length-range": f"{size_bytes},{size_bytes}",
            },
            expires_at,
        )

    def head(self, bucket: str, key: str) -> ObjectInfo:
        found = self.object_at(bucket, key)
        etag = hashlib.md5(found.data, usedforsecurity=False).hexdigest()
        return ObjectInfo(len(found.data), found.media_type, etag)

    @contextmanager
    def read_stream(self, bucket: str, key: str) -> Iterator[Iterator[bytes]]:
        found = self.object_at(bucket, key)
        yield iter([found.data[index : index + 1024] for index in range(0, len(found.data), 1024)])

    def copy(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        source_etag: str,
    ) -> None:
        source = self.object_at(source_bucket, source_key)
        if hashlib.md5(source.data, usedforsecurity=False).hexdigest() != source_etag:
            raise StorageInvalid()
        if destination_key in self.buckets.get(destination_bucket, {}):
            raise StorageInvalid()
        self.put(destination_bucket, destination_key, source.data, source.media_type)

    def delete(self, bucket: str, key: str) -> None:
        if self.unavailable:
            raise StorageUnavailable()
        if self.buckets.get(bucket, {}).pop(key, None) is None:
            raise StorageMissing()

    def list_keys(self, bucket: str, prefix: str) -> Iterator[tuple[str, datetime]]:
        if self.unavailable:
            raise StorageUnavailable()
        for key, value in sorted(self.buckets.get(bucket, {}).items()):
            if key.startswith(prefix):
                yield key, value.modified
