from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from minio import Minio
from minio.commonconfig import CopySource
from minio.datatypes import PostPolicy
from minio.error import MinioException, S3Error

from app.modules.portfolio.limits import STREAM_CHUNK_BYTES
from app.shared.errors import StorageInvalid, StorageMissing, StorageUnavailable
from app.shared.ports import ObjectInfo, PresignedPost

MISSING = frozenset({"NoSuchKey", "NoSuchObject", "NotFound"})


def mapped(error: Exception) -> Exception:
    """Absent, invalid and unavailable stay distinct; a failure is never a success."""
    if isinstance(error, S3Error) and error.code in MISSING:
        return StorageMissing()
    if isinstance(error, S3Error) and error.code == "PreconditionFailed":
        return StorageInvalid()
    return StorageUnavailable()


class MinioStorage:
    """Private-bucket adapter: presigned POST only, no signed GET is ever produced."""

    def __init__(self, client: Minio, public_endpoint: str) -> None:
        self.client, self.public_endpoint = client, public_endpoint.rstrip("/")

    def presign_post(
        self, bucket: str, key: str, media_type: str, size_bytes: int, expires_at: datetime
    ) -> PresignedPost:
        policy = PostPolicy(bucket, expires_at)
        policy.add_equals_condition("key", key)
        policy.add_equals_condition("Content-Type", media_type)
        policy.add_content_length_range_condition(size_bytes, size_bytes)
        try:
            fields = self.client.presigned_post_policy(policy)
        except (MinioException, OSError, ValueError) as error:
            raise mapped(error) from None
        # The form must carry the exact key and type the policy pins; clients only forward them.
        form = {**fields, "key": key, "Content-Type": media_type}
        return PresignedPost(f"{self.public_endpoint}/{bucket}", form, expires_at)

    def head(self, bucket: str, key: str) -> ObjectInfo:
        try:
            info = self.client.stat_object(bucket, key)
        except (MinioException, OSError) as error:
            raise mapped(error) from None
        if info.size is None or info.etag is None:
            raise StorageInvalid()
        media_type = info.content_type or "application/octet-stream"
        return ObjectInfo(info.size, media_type, info.etag.strip('"'))

    @contextmanager
    def read_stream(self, bucket: str, key: str) -> Iterator[Iterator[bytes]]:
        try:
            response = self.client.get_object(bucket, key)
        except (MinioException, OSError) as error:
            raise mapped(error) from None
        try:
            yield response.stream(STREAM_CHUNK_BYTES)
        finally:
            response.close()
            response.release_conn()

    def copy(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str,
        destination_key: str,
        source_etag: str,
    ) -> None:
        source = CopySource(source_bucket, source_key, match_etag=source_etag)
        try:
            self.client.copy_object(destination_bucket, destination_key, source)
        except (MinioException, OSError) as error:
            raise mapped(error) from None

    def delete(self, bucket: str, key: str) -> None:
        try:
            self.client.remove_object(bucket, key)
        except (MinioException, OSError) as error:
            raise mapped(error) from None

    def list_keys(self, bucket: str, prefix: str) -> Iterator[tuple[str, datetime]]:
        try:
            for item in self.client.list_objects(bucket, prefix=prefix, recursive=True):
                if item.object_name is not None and item.last_modified is not None:
                    yield item.object_name, item.last_modified
        except (MinioException, OSError) as error:
            raise mapped(error) from None
