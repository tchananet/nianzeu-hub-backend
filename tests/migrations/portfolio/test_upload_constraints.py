from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.migrations.identity.helpers import NOW
from tests.migrations.portfolio.helpers import item, upload

pytestmark = pytest.mark.integration


@pytest.fixture
def owned_item(portfolio_db, owned_profile):
    return item(portfolio_db, owned_profile, state="pending")


def count_uploads(connection):
    return connection.execute(text("SELECT count(*) FROM portfolio_uploads")).scalar_one()


@pytest.mark.parametrize("changes", [
    {"id": None}, {"item_id": None}, {"quarantine_key": None}, {"quarantine_key": ""},
    {"filename": None}, {"filename": ""}, {"media_type": None}, {"media_type": ""},
    {"size_bytes": None}, {"size_bytes": 0}, {"size_bytes": -1}, {"size_bytes": 104857601},
    {"sha256": None}, {"sha256": "B" * 64}, {"sha256": "z" * 64}, {"created_at": None},
    {"expires_at": None}, {"expires_at": NOW}, {"expires_at": NOW - timedelta(seconds=1)},
    {"reservation_active": None},
])
def test_invalid_upload_rejected(portfolio_db, owned_item, changes):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        upload(portfolio_db, owned_item, **changes)


def test_one_current_upload_per_item(portfolio_db, owned_profile, owned_item):
    upload(portfolio_db, owned_item)
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        upload(portfolio_db, owned_item)
    other = item(portfolio_db, owned_profile, state="pending")
    upload(portfolio_db, other)
    assert count_uploads(portfolio_db) == 2


def test_quarantine_key_unique(portfolio_db, owned_profile, owned_item):
    upload(portfolio_db, owned_item, quarantine_key="quarantine/shared")
    other = item(portfolio_db, owned_profile, state="pending")
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        upload(portfolio_db, other, quarantine_key="quarantine/shared")


def test_item_foreign_key_and_cascade(portfolio_db, owned_profile, owned_item):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        upload(portfolio_db, uuid4())
    upload(portfolio_db, owned_item)
    portfolio_db.execute(text("DELETE FROM portfolio_items WHERE id=:id"), {"id": owned_item})
    assert count_uploads(portfolio_db) == 0
    other = item(portfolio_db, owned_profile, state="pending")
    upload(portfolio_db, other)
    portfolio_db.execute(text("DELETE FROM talent_profiles WHERE id=:id"), {"id": owned_profile})
    assert count_uploads(portfolio_db) == 0


def test_lease_nullable_and_reservation_flag_persisted(portfolio_db, owned_item):
    ident = upload(portfolio_db, owned_item, lease_until=None, reservation_active=False)
    row = portfolio_db.execute(
        text("SELECT lease_until, reservation_active FROM portfolio_uploads WHERE id=:id"),
        {"id": ident},
    )
    assert row.one() == (None, False)
    portfolio_db.execute(
        text("UPDATE portfolio_uploads SET lease_until=:lease, reservation_active=true"),
        {"lease": NOW + timedelta(seconds=60)},
    )
    assert count_uploads(portfolio_db) == 1
