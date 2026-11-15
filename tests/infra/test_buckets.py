from unittest.mock import Mock

import pytest
from minio.error import S3Error
from urllib3.exceptions import ReadTimeoutError

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


def test_a_warming_storage_service_is_waited_for_not_failed(health_client):
    # The real failure: SeaweedFS accepted the connection but did not answer the
    # bucket creation inside one request timeout, so bootstrap exited 1 and took the
    # whole deployment with it.
    _, _, storage = health_client
    timeout = ReadTimeoutError(None, "/quarantine", "Read timed out. (read timeout=2)")
    storage.bucket_exists.side_effect = [timeout, False, True]
    initialize_buckets(attempts=3, pause=0)
    assert storage.make_bucket.call_count == 1


def test_a_storage_service_that_never_answers_still_fails(health_client):
    _, _, storage = health_client
    storage.bucket_exists.side_effect = ReadTimeoutError(None, "/quarantine", "timed out")
    with pytest.raises(ReadTimeoutError):
        initialize_buckets(attempts=2, pause=0)


def test_invalid_config_prevents_startup(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr("app.main.Settings", Mock(side_effect=ValueError("Invalid config")))
    with pytest.raises(ValueError, match="Invalid config"), TestClient(create_app()):
        pass
