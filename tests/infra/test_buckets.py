from unittest.mock import Mock

import pytest
from minio.error import S3Error

from app.main import initialize_buckets


def test_initialization_is_idempotent_and_removes_policies(health_client):
    _, _, storage = health_client
    storage.bucket_exists.side_effect = [False, False, True, True]
    initialize_buckets()
    initialize_buckets()
    assert storage.make_bucket.call_count == 2
    assert [call.args[0] for call in storage.delete_bucket_policy.call_args_list] == [
        "quarantine", "validated", "quarantine", "validated",
    ]


def s3_error(code: str) -> S3Error:
    # minio>=7.2 takes the response first; keywords keep the code in the right slot.
    return S3Error(response=None, code=code, message="refused",
                   resource="bucket", request_id="request", host_id="host")


def test_initialization_fails_on_denied_policy_removal(health_client):
    _, _, storage = health_client
    storage.delete_bucket_policy.side_effect = s3_error("AccessDenied")
    with pytest.raises(S3Error):
        initialize_buckets()


@pytest.mark.parametrize("code", ["NoSuchBucketPolicy", "NotImplemented"])
def test_a_bucket_with_no_policy_to_delete_is_already_in_the_wanted_state(
    health_client, code: str
) -> None:
    # MinIO deleted a missing policy silently; other S3 implementations raise, and one
    # may not implement bucket policies at all. Both mean no anonymous policy remains,
    # so bootstrap must not treat either as a failure.
    _, _, storage = health_client
    storage.bucket_exists.return_value = True
    storage.delete_bucket_policy.side_effect = s3_error(code)
    initialize_buckets()
    assert storage.delete_bucket_policy.call_count == 2


def test_invalid_config_prevents_startup(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr("app.main.Settings", Mock(side_effect=ValueError("Invalid config")))
    with pytest.raises(ValueError, match="Invalid config"), TestClient(create_app()):
        pass
