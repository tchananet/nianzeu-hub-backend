from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.migrations.identity.helpers import insert
from tests.migrations.profiles.helpers import SKILL_ID, profile

pytestmark = pytest.mark.integration


def test_contact_defaults(profiles_db):
    ident = profile(profiles_db)
    insert(profiles_db, "contact_settings", profile_id=ident)
    row = profiles_db.execute(text("SELECT * FROM contact_settings")).mappings().one()
    for field in ("email", "phone", "whatsapp"):
        assert row[field] is None
        assert row[f"{field}_visible"] is False


@pytest.mark.parametrize("field,value", [
    ("email", "public@example.test"), ("phone", "+237612345678"), ("whatsapp", "+237612345678"),
])
def test_visible_requires_value(profiles_db, field, value):
    ident = profile(profiles_db)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "contact_settings", profile_id=ident, **{f"{field}_visible": True})
    insert(profiles_db, "contact_settings", profile_id=ident,
           **{field: value, f"{field}_visible": True})
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        profiles_db.execute(text(f"UPDATE contact_settings SET {field}=NULL"))
    profiles_db.execute(text("DELETE FROM talent_profiles WHERE id=:id"), {"id": ident})
    assert profiles_db.execute(text("SELECT count(*) FROM contact_settings")).scalar_one() == 0


def test_contact_fk_and_unique(profiles_db):
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "contact_settings", profile_id=uuid4())
    ident = profile(profiles_db)
    insert(profiles_db, "contact_settings", profile_id=ident)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "contact_settings", profile_id=ident)


def test_skill_fk_unique_restrict_and_profile_cascade(profiles_db):
    ident = profile(profiles_db)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "profile_skills", profile_id=ident, skill_id=uuid4())
    insert(profiles_db, "profile_skills", profile_id=ident, skill_id=SKILL_ID)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "profile_skills", profile_id=ident, skill_id=SKILL_ID)
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        profiles_db.execute(text("DELETE FROM skills WHERE id=:id"), {"id": SKILL_ID})
    profiles_db.execute(text("DELETE FROM talent_profiles WHERE id=:id"), {"id": ident})
    assert profiles_db.execute(text("SELECT count(*) FROM profile_skills")).scalar_one() == 0
    assert profiles_db.execute(text("SELECT count(*) FROM skills")).scalar_one() == 6


@pytest.mark.parametrize("name,normalized", [
    ("Python", "python"), ("Python2", "PYTHON2"), ("", ""),
])
def test_skill_normalization_and_unique(profiles_db, name, normalized):
    with pytest.raises(IntegrityError), profiles_db.begin_nested():
        insert(profiles_db, "skills", id=uuid4(), name=name, normalized_name=normalized)
