import os
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import build_engine
from app.main import check_buckets, storage_client

pytestmark = pytest.mark.skipif(
    os.getenv("F02_STACK_TEST") != "1", reason="requires isolated F02 Compose stack",
)


def test_real_health_without_business_tables():
    settings = Settings()
    assert settings.environment == "test", "isolated test environment required"
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            assert connection.execute(text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )).scalar_one() == 0
    finally:
        engine.dispose()
    base = os.environ["F02_API_URL"]
    for route, status in [("live", "ok"), ("ready", "ready")]:
        response = httpx.get(f"{base}/health/{route}", timeout=25)
        assert response.status_code == 200
        assert response.json() == {"status": status}
        assert response.headers["x-request-id"]


def test_both_buckets_deny_anonymous_listing_and_object_reads():
    settings = Settings()
    assert settings.environment == "test"
    storage = storage_client(settings)
    check_buckets(storage, settings)
    for bucket in (settings.quarantine_bucket, settings.validated_bucket):
        key = f"f02-probe-{uuid4()}"
        storage.put_object(bucket, key, BytesIO(b"private"), 7)
        try:
            for path in (f"/{bucket}?list-type=2", f"/{bucket}/{key}"):
                response = httpx.get(settings.storage_endpoint + path, timeout=5)
                assert response.status_code == 403
        finally:
            storage.remove_object(bucket, key)
