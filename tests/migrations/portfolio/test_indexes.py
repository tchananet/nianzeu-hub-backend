import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration
EXPECTED = {
    "ix_portfolio_items_profile_state_published": ("profile_id", "state", "published_at", "id"),
    "ix_talent_profiles_updated_at_id": ("updated_at DESC", "id"),
    "ix_talent_profiles_availability": ("availability",),
    "ix_talent_profiles_experience_level": ("experience_level",),
    "ix_talent_profiles_country_city": ("country_code", "lower(", "city"),
    "ix_profile_skills_skill_profile": ("skill_id", "profile_id"),
}
PRIVATE = ("email", "phone", "whatsapp")
SAMPLE = "00000000-0000-4000-8000-00000000000a"
SKILL = "00000000-0000-4000-8000-000000000001"


def definitions(connection):
    rows = connection.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = current_schema()"
    ))
    return {row.indexname: row.indexdef for row in rows}


def test_declared_indexes_present_with_ordered_keys(portfolio_db):
    found = definitions(portfolio_db)
    for name, tokens in EXPECTED.items():
        assert name in found, name
        remaining = found[name].split("USING btree ", 1)[1]
        for token in tokens:
            assert token in remaining, (name, token)
            remaining = remaining.split(token, 1)[1]
    assert "id DESC" not in found["ix_talent_profiles_updated_at_id"]


def test_no_index_on_private_contact_columns(portfolio_db):
    for name, definition in definitions(portfolio_db).items():
        if "contact_settings" not in definition:
            continue
        keys = definition.split("USING btree ", 1)[1]
        assert not any(column in keys for column in PRIVATE), name


def test_no_trigram_or_non_btree_index_required(portfolio_db):
    for name, definition in definitions(portfolio_db).items():
        assert "USING btree " in definition, name
        assert "trgm" not in definition, name
    installed = portfolio_db.execute(
        text("SELECT count(*) FROM pg_extension WHERE extname = 'pg_trgm'")
    ).scalar_one()
    assert installed == 0


@pytest.mark.parametrize("query,index", [
    (
        "SELECT id FROM talent_profiles ORDER BY updated_at DESC, id ASC LIMIT 20",
        "ix_talent_profiles_updated_at_id",
    ),
    (
        f"SELECT id FROM portfolio_items WHERE profile_id = '{SAMPLE}'::uuid"
        " AND state = 'published' ORDER BY published_at DESC, id ASC LIMIT 20",
        "ix_portfolio_items_profile_state_published",
    ),
    (
        f"SELECT profile_id FROM profile_skills WHERE skill_id = '{SKILL}'::uuid",
        "ix_profile_skills_skill_profile",
    ),
])
def test_search_indexes_are_usable(portfolio_db, query, index):
    portfolio_db.execute(text("SET LOCAL enable_seqscan = off"))
    plan = portfolio_db.execute(text(f"EXPLAIN {query}")).scalars().all()
    assert any(index in line for line in plan), plan
