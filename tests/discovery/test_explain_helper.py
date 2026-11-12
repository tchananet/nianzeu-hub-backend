from uuid import UUID

from sqlalchemy.dialects import postgresql

from app.modules.discovery.filters import skill_subquery
from tests.discovery.explain import page_statement

SKILLS = [UUID(f"00000000-0000-4000-8000-{i:012d}") for i in (1, 4)]


def rendered(statement):
    compiled = statement.compile(
        dialect=postgresql.dialect(), compile_kwargs={"render_postcompile": True})
    return str(compiled), dict(compiled.params)


def test_page_statement_mirrors_the_repository_order_and_window():
    sql, params = rendered(page_statement(page=2, page_size=50))
    assert "ORDER BY talent_profiles.updated_at DESC, talent_profiles.id ASC" in sql
    assert params["param_1"] == 50 and params["param_2"] == 50


def test_explained_statements_are_fully_rendered_for_the_driver():
    statements = [
        page_statement(q="a%b", city="Douala", country_code="CM", availability="immediate",
                       experience_level="senior", skill_id=[str(value) for value in SKILLS]),
        skill_subquery(SKILLS),
    ]
    for statement in statements:
        sql, params = rendered(statement)
        assert "POSTCOMPILE" not in sql, sql
        assert params and all(f"%({name})s" in sql for name in params), sql
