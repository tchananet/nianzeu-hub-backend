import base64
import json
from datetime import UTC, datetime, timedelta

from minio import Minio

from app.modules.portfolio.minio_storage import MinioStorage

EXPIRES = datetime.now(UTC) + timedelta(minutes=5)


def adapter() -> MinioStorage:
    client = Minio(
        "minio.internal:9000", access_key="ak", secret_key="sk", secure=False, region="us-east-1"
    )
    return MinioStorage(client, "https://files.test/")


def test_presigned_form_pins_bucket_key_type_and_exact_length() -> None:
    signed = adapter().presign_post("quarantine", "quarantine/a/b", "image/png", 123, EXPIRES)
    assert signed.url == "https://files.test/quarantine"
    assert signed.fields["key"] == "quarantine/a/b"
    assert signed.fields["Content-Type"] == "image/png"
    policy = json.loads(base64.b64decode(signed.fields["policy"]))
    assert ["eq", "$bucket", "quarantine"] in policy["conditions"]
    assert ["eq", "$key", "quarantine/a/b"] in policy["conditions"]
    assert ["eq", "$Content-Type", "image/png"] in policy["conditions"]
    assert ["content-length-range", 123, 123] in policy["conditions"]
    assert policy["expiration"].endswith("Z")


def test_expiry_never_exceeds_five_minutes() -> None:
    signed = adapter().presign_post("quarantine", "k", "image/png", 1, EXPIRES)
    policy = json.loads(base64.b64decode(signed.fields["policy"]))
    expiration = datetime.fromisoformat(policy["expiration"].replace("Z", "+00:00"))
    assert expiration - datetime.now(UTC) <= timedelta(minutes=5, seconds=1)


def test_no_signed_get_url_is_exposed_by_the_adapter() -> None:
    exported = {name for name in dir(MinioStorage) if not name.startswith("_")}
    assert exported == {
        "presign_post", "head", "read_stream", "copy", "delete", "list_keys",
    }
    assert not any("get_object" in name or "presign_get" in name for name in exported)
