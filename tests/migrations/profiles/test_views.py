from datetime import date, timedelta

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from tests.migrations.identity.helpers import NOW, insert
from tests.migrations.profiles.helpers import profile

pytestmark = pytest.mark.integration


def test_view_count_dedup_and_cascade(profiles_db):
    ident = profile(profiles_db)
    day = date(2026, 1, 1)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "profile_views", profile_id=ident, day=day, count=-1)
    insert(profiles_db, "profile_views", profile_id=ident, day=day, count=1)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "profile_views", profile_id=ident, day=day, count=2)
    values = dict(profile_id=ident, day=day, visitor_hash="a" * 64,
                  expires_at=NOW + timedelta(days=2))
    insert(profiles_db, "profile_view_dedup", **values)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "profile_view_dedup", **values)
    insert(profiles_db, "profile_view_dedup", **{**values, "day": day + timedelta(days=1)})
    profiles_db.execute(text("DELETE FROM talent_profiles WHERE id=:id"), {"id": ident})
    for table in ("profile_views", "profile_view_dedup"):
        assert profiles_db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


def test_expiration_index_and_no_private_indexes(profiles_db):
    inspector = inspect(profiles_db)
    assert any(index["column_names"] == ["expires_at"]
               for index in inspector.get_indexes("profile_view_dedup"))
    for index in inspector.get_indexes("contact_settings"):
        assert not {"email", "phone", "whatsapp"}.intersection(index["column_names"])
