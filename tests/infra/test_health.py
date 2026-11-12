from uuid import UUID

import pytest
from minio.error import MinioException, S3Error
from sqlalchemy.exc import OperationalError
from urllib3.exceptions import HTTPError


def s3_error(code):
    # minio>=7.2 takes the response first; keywords keep the code in the right slot.
    return S3Error(response=None, code=code, message="sensitive detail",
                   resource="bucket", request_id="request", host_id="host")


def test_ready_checks_both_private_buckets_without_schema(health_client):
    client, engine, storage = health_client
    storage.get_bucket_policy.side_effect = s3_error("NoSuchBucketPolicy")
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    UUID(response.headers["x-request-id"])
    connection = engine.connect.return_value.__enter__.return_value
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"
    assert [call.args[0] for call in storage.bucket_exists.call_args_list] == [
        "quarantine", "validated",
    ]


@pytest.mark.parametrize("failure", ["db", "missing", "public", "denied", "network", "s3"])
def test_dependency_failure_is_private_and_liveness_survives(health_client, failure):
    client, engine, storage = health_client
    storage.get_bucket_policy.side_effect = s3_error("NoSuchBucketPolicy")
    if failure == "db":
        engine.connect.side_effect = OperationalError("secret SQL", {}, Exception("secret"))
    elif failure == "missing":
        storage.bucket_exists.return_value = False
    elif failure == "public":
        storage.get_bucket_policy.side_effect = None
        storage.get_bucket_policy.return_value = '{"Statement":[]}'
    elif failure == "denied":
        storage.get_bucket_policy.side_effect = s3_error("AccessDenied")
    elif failure == "s3":
        storage.bucket_exists.side_effect = MinioException("secret response")
    else:
        storage.bucket_exists.side_effect = HTTPError("secret endpoint")
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {
        "error": {"code": "DEPENDENCY_UNAVAILABLE", "message": "Dependency unavailable",
                  "details": []},
        "request_id": response.headers["x-request-id"],
    }
    live = client.get("/health/live")
    assert live.status_code == 200 and live.json() == {"status": "ok"}


def test_framework_errors_are_enveloped(health_client):
    client, _, _ = health_client
    for method, path, status in [("get", "/absent", 404), ("post", "/health/live", 405)]:
        response = getattr(client, method)(path)
        assert response.status_code == status
        assert response.json()["request_id"] == response.headers["x-request-id"]
