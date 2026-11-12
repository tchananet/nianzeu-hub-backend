from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests.migrations.portfolio.helpers import item, validated_item

pytestmark = pytest.mark.integration


def count_items(connection):
    return connection.execute(text("SELECT count(*) FROM portfolio_items")).scalar_one()


@pytest.mark.parametrize("changes", [
    {"type": "link"}, {"type": ""}, {"type": None}, {"state": "archived"}, {"state": ""},
    {"state": None}, {"title": ""}, {"title": None}, {"description": None},
    {"created_at": None}, {"updated_at": None}, {"profile_id": None}, {"id": None},
    {"rejection_code": ""},
])
def test_invalid_item_rejected(portfolio_db, owned_profile, changes):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        item(portfolio_db, owned_profile, **changes)


@pytest.mark.parametrize("changes", [
    {"size_bytes": 0}, {"size_bytes": -1}, {"size_bytes": 104857601},
    {"sha256": "B" * 64}, {"sha256": "z" * 64}, {"object_key": ""},
    {"filename": ""}, {"media_type": ""},
])
def test_invalid_final_metadata_rejected(portfolio_db, owned_profile, changes):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        validated_item(portfolio_db, owned_profile, **changes)


@pytest.mark.parametrize("size", [1, 104857600])
def test_size_bounds_accepted(portfolio_db, owned_profile, size):
    validated_item(portfolio_db, owned_profile, size_bytes=size)
    assert count_items(portfolio_db) == 1


def test_rejected_state_keeps_rejection_code(portfolio_db, owned_profile):
    item(portfolio_db, owned_profile, state="rejected", rejection_code="INVALID_UPLOAD")
    row = portfolio_db.execute(text("SELECT state, rejection_code FROM portfolio_items"))
    assert row.one() == ("rejected", "INVALID_UPLOAD")


def test_object_key_unique_and_null_allowed_many_times(portfolio_db, owned_profile):
    validated_item(portfolio_db, owned_profile, object_key="final/shared")
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        validated_item(portfolio_db, owned_profile, object_key="final/shared")
    item(portfolio_db, owned_profile)
    item(portfolio_db, owned_profile)
    assert count_items(portfolio_db) == 3


def test_profile_foreign_key_and_cascade(portfolio_db, owned_profile):
    with pytest.raises(IntegrityError), portfolio_db.begin_nested():
        item(portfolio_db, uuid4())
    item(portfolio_db, owned_profile)
    portfolio_db.execute(text("DELETE FROM talent_profiles WHERE id=:id"), {"id": owned_profile})
    assert count_items(portfolio_db) == 0


def test_timestamp_columns_are_timezone_aware(portfolio_db):
    for table in ("portfolio_items", "portfolio_uploads"):
        for column in inspect(portfolio_db).get_columns(table):
            if column["name"].endswith(("_at", "_until")):
                assert column["type"].timezone is True
