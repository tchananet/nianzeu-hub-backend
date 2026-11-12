from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.modules.discovery.filters import conditions, literal_pattern, skill_subquery
from app.modules.discovery.schemas import SearchQuery
from app.modules.profiles.models import Profile

SKILLS = [UUID(f"00000000-0000-4000-8000-{i:012d}") for i in (1, 2)]
BACKSLASH = chr(92)


def compiled(**kwargs):
    query = SearchQuery.model_validate(kwargs)
    statement = select(Profile).where(*conditions(query))
    return statement.compile(dialect=postgresql.dialect())


def test_wildcards_and_escape_are_literals():
    assert literal_pattern("50%_A" + BACKSLASH + "b") == (
        "%50" + BACKSLASH + "%" + BACKSLASH + "_a" + BACKSLASH * 2 + "b%")
    assert literal_pattern("") == "%%"


def test_keyword_searches_public_text_columns_only():
    sql = str(compiled(q="Ada%"))
    for column in ("display_name", "headline", "bio"):
        assert f"lower(talent_profiles.{column}) LIKE" in sql
    assert compiled(q="Ada%").params["lower_1"] == "%ada" + BACKSLASH + "%%"


def test_city_uses_the_lower_expression_index_shape():
    assert "lower(talent_profiles.city) = " in str(compiled(city="DoUaLa"))
    assert compiled(city="DoUaLa").params["lower_1"] == "douala"


def test_scalar_filters_compile_to_equality():
    sql = str(compiled(country_code="CM", availability="freelance", experience_level="senior"))
    for column in ("country_code", "availability", "experience_level"):
        assert f"talent_profiles.{column} = " in sql


def test_skill_filter_requires_every_skill():
    sql = str(skill_subquery(SKILLS).compile(dialect=postgresql.dialect()))
    assert "profile_skills.skill_id IN" in sql
    assert "GROUP BY profile_skills.profile_id" in sql
    assert "HAVING count(DISTINCT profile_skills.skill_id) = " in sql
    assert "talent_profiles.id IN (SELECT profile_skills.profile_id" in str(
        compiled(skill_id=[str(value) for value in SKILLS]))


def test_no_filter_touches_private_tables_or_columns():
    sql = str(compiled(q="a", city="b", country_code="CM", availability="immediate",
                       experience_level="junior", skill_id=[str(SKILLS[0])]))
    for forbidden in ("contact_settings", "email", "phone", "whatsapp", "users", "sessions"):
        assert forbidden not in sql


def test_empty_query_yields_no_clause():
    assert conditions(SearchQuery()) == []
    assert "WHERE" not in str(compiled())
