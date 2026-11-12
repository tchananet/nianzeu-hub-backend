import pytest
from sqlalchemy import text

from tests.discovery.explain import index_definitions

pytestmark = pytest.mark.integration

EXPECTED = [
    ("talent_profiles", ("updated_at DESC", "id)")),
    ("talent_profiles", ("(availability)",)),
    ("talent_profiles", ("(experience_level)",)),
    ("talent_profiles", ("country_code", "lower(")),
    ("profile_skills", ("skill_id, profile_id",)),
]


@pytest.mark.parametrize("table,fragments", EXPECTED)
def test_m03_search_indexes_exist(discovery_db, table, fragments):
    factory, _ = discovery_db
    with factory.begin() as db:
        definitions = index_definitions(db, table)
    matches = [one for one in definitions
               if all(fragment in one for fragment in fragments)]
    assert matches, (fragments, definitions)


def test_no_trigram_extension_is_required(discovery_db):
    factory, _ = discovery_db
    with factory.begin() as db:
        installed = db.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'pg_trgm'"))
        definitions = index_definitions(db, "talent_profiles")
    assert installed == 0
    assert not [one for one in definitions if "gin" in one.lower() or "gist" in one.lower()]


def test_no_index_covers_private_contact_columns(discovery_db):
    factory, _ = discovery_db
    with factory.begin() as db:
        definitions = index_definitions(db, "contact_settings")
    for definition in definitions:
        for column in ("email", "phone", "whatsapp"):
            assert column not in definition, definition
