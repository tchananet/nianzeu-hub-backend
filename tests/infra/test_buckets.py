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


def test_initialization_fails_on_denied_policy_removal(health_client):
    _, _, storage = health_client
    storage.delete_bucket_policy.side_effect = S3Error(
        "AccessDenied", "denied", "bucket", "request", "host", None,
    )
    with pytest.raises(S3Error):
        initialize_buckets()


def test_invalid_config_prevents_startup(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr("app.main.Settings", Mock(side_effect=ValueError("Invalid config")))
    with pytest.raises(ValueError, match="Invalid config"), TestClient(create_app()):
        pass
