"""Seed/verify/clean only UUID-scoped test data across container recreation."""

import os
import sys
from io import BytesIO
from uuid import UUID

from sqlalchemy import text

from app.core.config import Settings
from app.core.database import build_engine
from app.main import check_buckets, storage_client


def main():
    settings = Settings()
    assert settings.environment == "test" and os.environ["F02_STACK_TEST"] == "1"
    probe = str(UUID(os.environ["F02_PROBE_ID"]))
    action = sys.argv[1]
    assert action in ("seed", "verify", "clean")
    payload = f"f02-persistence-{probe}".encode()
    key = f"f02-probe/{probe}"
    engine, storage = build_engine(settings), storage_client(settings)
    check_buckets(storage, settings)
    try:
        with engine.begin() as connection:
            if action == "seed":
                connection.execute(text("CREATE SCHEMA IF NOT EXISTS f02_infra_probe"))
                connection.execute(text(
                    "CREATE TABLE IF NOT EXISTS f02_infra_probe.persistence "
                    "(id uuid PRIMARY KEY, payload text NOT NULL)"
                ))
                connection.execute(text(
                    "INSERT INTO f02_infra_probe.persistence VALUES (:id, :payload)"
                ), {"id": probe, "payload": payload.decode()})
            elif action == "verify":
                actual = connection.execute(text(
                    "SELECT payload FROM f02_infra_probe.persistence WHERE id=:id"
                ), {"id": probe}).scalar_one()
                assert actual == payload.decode()
            else:
                connection.execute(text(
                    "DELETE FROM f02_infra_probe.persistence WHERE id=:id"
                ), {"id": probe})
        for bucket in (settings.quarantine_bucket, settings.validated_bucket):
            if action == "seed":
                storage.put_object(bucket, key, BytesIO(payload), len(payload))
            elif action == "verify":
                response = storage.get_object(bucket, key)
                try:
                    assert response.read() == payload
                finally:
                    response.close()
                    response.release_conn()
            else:
                storage.remove_object(bucket, key)
    finally:
        engine.dispose()
    print(f"F02 persistence {action}: PASS ({probe})")


if __name__ == "__main__":
    main()
