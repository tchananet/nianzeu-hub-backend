from datetime import UTC

import pytest

from app.core.primitives import ip_quota_key, new_secret, quota_key, secret_hash, utc_now
from app.shared.errors import EmailUnavailable, StorageInvalid, StorageMissing, StorageUnavailable
from app.shared.ports import DisabledEmail, EmailPort


def test_disabled_email_never_reports_success():
    email: EmailPort = DisabledEmail()
    with pytest.raises(EmailUnavailable) as error:
        email.send_password_reset("private@example.test", "https://secret.test/token")
    assert error.value.status == 503
    assert "private" not in str(error.value)
    assert "token" not in str(error.value)


def test_storage_failure_categories_are_distinct():
    for error in (StorageMissing(), StorageInvalid(), StorageUnavailable()):
        with pytest.raises(type(error)):
            raise error
    assert not issubclass(StorageMissing, StorageUnavailable)
    assert not issubclass(StorageInvalid, StorageMissing)
    assert StorageUnavailable().code == "DEPENDENCY_UNAVAILABLE"


def test_secret_and_clock():
    first, second = new_secret(), new_secret()
    assert first != second and len(first) == len(second) == 43
    assert len(secret_hash(first)) == 64
    assert first not in secret_hash(first)
    assert utc_now().tzinfo is UTC


def test_hmac_normalizes_ips_and_separates_keys():
    assert ip_quota_key("secret", "::ffff:127.0.0.1") == ip_quota_key("secret", "127.0.0.1")
    assert ip_quota_key("secret", "::1") == ip_quota_key("secret", "0:0:0:0:0:0:0:1")
    assert quota_key("one", "email") != quota_key("two", "email")
    assert quota_key("one", "email") != quota_key("one", "other")
