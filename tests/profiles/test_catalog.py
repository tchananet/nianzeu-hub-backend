import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.modules.profiles.catalog import SkillsQuery, list_skills, parse_query


@pytest.mark.parametrize("query", [
    "page=0", "page=1&page=2", "q=", "q=x&q=y", "unknown=x", "page_size=51", "page=true",
])
def test_invalid_catalog_query(query):
    request = Request({"type": "http", "query_string": query.encode(), "headers": []})
    with pytest.raises(RequestValidationError):
        parse_query(request)


@pytest.mark.integration
def test_catalog_literal_search_and_pagination(profile_db):
    factory, _ = profile_db
    result = list_skills(factory, SkillsQuery(q="pYtHoN"))
    assert [skill.name for skill in result.items] == ["Python"]
    assert list_skills(factory, SkillsQuery(q="%")).total == 0
    assert list_skills(factory, SkillsQuery(q="_")).total == 0
    page = list_skills(factory, SkillsQuery(page_size=2))
    assert page.total == 6 and len(page.items) == 2
    assert page.items != list_skills(factory, SkillsQuery(page_size=2, page=2)).items
