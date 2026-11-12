from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.migrations.profiles.helpers import entry, profile

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("table", ["experiences", "certifications"])
@pytest.mark.parametrize("position", [-1, 20])
def test_position_bounds(profiles_db, table, position):
    ident = profile(profiles_db)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        entry(profiles_db, table, ident, position=position)


@pytest.mark.parametrize("table", ["experiences", "certifications"])
def test_position_uniqueness_and_parent_fk(profiles_db, table):
    ident = profile(profiles_db)
    entry(profiles_db, table, ident)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        entry(profiles_db, table, ident)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        entry(profiles_db, table, uuid4())
    entry(profiles_db, table, ident, position=19)
    other = profile(profiles_db)
    entry(profiles_db, table, other)


@pytest.mark.parametrize("table,field", [
    ("experiences", "end_date"), ("certifications", "expires_on"),
])
def test_dates_ordered_nullable_and_equal(profiles_db, table, field):
    ident = profile(profiles_db)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        entry(profiles_db, table, ident, **{field: date(2024, 12, 31)})
    entry(profiles_db, table, ident, **{field: None})
    entry(profiles_db, table, ident, position=1, **{field: date(2025, 1, 1)})


@pytest.mark.parametrize("table,field", [
    ("experiences", "title"), ("experiences", "organization"),
    ("certifications", "name"), ("certifications", "issuer"),
])
def test_required_strings_nonempty(profiles_db, table, field):
    ident = profile(profiles_db)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        entry(profiles_db, table, ident, **{field: ""})


def test_user_delete_cascades_profile_and_children(profiles_db):
    ident = profile(profiles_db)
    entry(profiles_db, "experiences", ident)
    entry(profiles_db, "certifications", ident)
    profiles_db.execute(text("DELETE FROM users"))
    for table in ("talent_profiles", "experiences", "certifications"):
        assert profiles_db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
