from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from minio.error import MinioException, S3Error

from app.modules.portfolio.minio_storage import MinioStorage, mapped
from app.shared.errors import StorageInvalid, StorageMissing, StorageUnavailable


def s3(code: str) -> S3Error:
    return S3Error(Mock(), code, "message", "resource", "request", "host")


@pytest.mark.parametrize("code", ["NoSuchKey", "NoSuchObject", "NotFound"])
def test_absent_objects_map_to_storage_missing(code: str) -> None:
    assert isinstance(mapped(s3(code)), StorageMissing)


def test_failed_etag_condition_maps_to_storage_invalid() -> None:
    assert isinstance(mapped(s3("PreconditionFailed")), StorageInvalid)


@pytest.mark.parametrize(
    "error", [s3("InternalError"), s3("NoSuchBucket"), MinioException("x"), OSError("x")]
)
def test_other_failures_never_look_like_success(error: Exception) -> None:
    assert isinstance(mapped(error), StorageUnavailable)


def test_head_failures_are_translated_not_swallowed() -> None:
    client = Mock()
    client.stat_object.side_effect = s3("NoSuchKey")
    storage = MinioStorage(client, "https://files.test")
    with pytest.raises(StorageMissing):
        storage.head("bucket", "key")
    client.presigned_post_policy.side_effect = MinioException("down")
    with pytest.raises(StorageUnavailable):
        storage.presign_post("bucket", "k", "image/png", 1, datetime.now(UTC) + timedelta(1))
