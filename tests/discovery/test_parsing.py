import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.modules.discovery.parsing import parse_search

SKILL = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
ELEVEN = "&".join(f"skill_id=00000000-0000-4000-8000-{i:012d}" for i in range(1, 12))


def request_for(query):
    return Request({"type": "http", "query_string": query.encode(), "headers": []})


@pytest.mark.parametrize("query", [
    "unknown=x", "sort=updated_at", "skill=1", "bio=x", "email=a@b.c",
    "page=0", "page=501", "page=1&page=2", "page=-1", "page=1.5", "page=100000",
    "page_size=0", "page_size=51", "page_size=true", "page=500&page_size=50",
    "q=", "q=%20%20", "q=" + "x" * 101, "q=a&q=b",
    "city=", "city=" + "c" * 101, "city=a&city=b",
    "country_code=cm", "country_code=CMR", "country_code=ZZ", "country_code=C1",
    "availability=weekly", "availability=", "experience_level=expert",
    "skill_id=nope", "skill_id=", f"skill_id={SKILL}&skill_id={SKILL}", ELEVEN,
])
def test_rejected_queries(query):
    with pytest.raises(RequestValidationError):
        parse_search(request_for(query))


def test_offset_cap_boundary_is_accepted():
    assert parse_search(request_for("page=201&page_size=50")).offset == 10000


def test_accepted_full_query():
    query = parse_search(request_for(
        f"q=Ada&skill_id={SKILL}&skill_id={OTHER}&city=Douala&country_code=CM"
        "&availability=freelance&experience_level=senior&page=2&page_size=5"))
    assert (query.q, query.city, query.country_code) == ("Ada", "Douala", "CM")
    assert [str(value) for value in query.skill_ids] == [SKILL, OTHER]
    assert (query.availability, query.experience_level) == ("freelance", "senior")
    assert (query.page, query.page_size, query.offset) == (2, 5, 5)


def test_defaults_and_trimming():
    query = parse_search(request_for("q=%20%20Ada%20%20"))
    assert query.q == "Ada" and query.skill_ids == []
    assert (query.page, query.page_size) == (1, 20)
    assert query.city is None and query.availability is None
    assert parse_search(request_for("")).model_dump() == query.model_dump() | {"q": None}


@pytest.mark.parametrize("query,field", [
    ("skill_id=nope", ("query", "skill_id")), ("page=0", ("query", "page")),
    ("country_code=ZZ", ("query", "country_code")), ("unknown=x", ("query", "unknown")),
])
def test_error_details_name_the_wire_parameter(query, field):
    with pytest.raises(RequestValidationError) as error:
        parse_search(request_for(query))
    locations = [tuple(item["loc"]) for item in error.value.errors()]
    assert all(found[: len(field)] == field for found in locations) and locations
