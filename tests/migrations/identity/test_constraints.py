from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.migrations.identity.helpers import NOW, child, insert, user

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("changes", [
    {"email": "UPPER@example.test"}, {"email": ""}, {"email": None},
    {"role": "admin"}, {"role": None}, {"created_at": None},
])
def test_invalid_user(migrated, changes):
    with pytest.raises(IntegrityError), migrated.begin_nested():
        user(migrated, **changes)


def test_unique_email_and_active_default(migrated):
    user(migrated, email="one@example.test")
    assert migrated.execute(text("SELECT is_active FROM users")).scalar_one() is True
    with pytest.raises(IntegrityError), migrated.begin_nested():
        user(migrated, email="one@example.test")


@pytest.mark.parametrize("table", ["credentials", "sessions", "password_reset_tokens"])
def test_foreign_key_and_cascade(migrated, table):
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, table, uuid4())
    owner = user(migrated)
    child(migrated, table, owner)
    migrated.execute(text("DELETE FROM users WHERE id = :id"), {"id": owner})
    assert migrated.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


@pytest.mark.parametrize("table", ["sessions", "password_reset_tokens"])
@pytest.mark.parametrize("changes", [
    {"expires_at": NOW}, {"token_hash": "plaintext"}, {"token_hash": None},
])
def test_invalid_token(migrated, table, changes):
    owner = user(migrated)
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, table, owner, **changes)


@pytest.mark.parametrize("table", ["sessions", "password_reset_tokens"])
def test_unique_token_hash(migrated, table):
    owner = user(migrated)
    child(migrated, table, owner, token_hash="a" * 64)
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, table, owner, token_hash="a" * 64)


@pytest.mark.parametrize("csrf", ["", "x" * 42, "!" * 43, None])
def test_csrf_shape(migrated, csrf):
    owner = user(migrated)
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, "sessions", owner, csrf_token=csrf)


def test_credentials_unique_and_nonempty(migrated):
    owner = user(migrated)
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, "credentials", owner, password_hash="")
    child(migrated, "credentials", owner)
    with pytest.raises(IntegrityError), migrated.begin_nested():
        child(migrated, "credentials", owner)


def test_negative_quota_rejected(migrated):
    with pytest.raises(IntegrityError), migrated.begin_nested():
        insert(migrated, "rate_limit_windows", scope="login", key_hash="a" * 64,
               window_start=NOW, expires_at=NOW, count=-1)
