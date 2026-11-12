import pytest

from tests.discovery.http_fixture import http_fixture, one_page
from tests.discovery.rows import PRIVATE_MARKERS, PUBLIC_FIELDS

URL = "/api/v1/search/profiles"


def test_anonymous_search_returns_collection_envelope():
    http, service, access = http_fixture()
    with http:
        response = http.get(URL)
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 20, "total": 0}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["vary"] == "Origin"
    assert access.calls == [""] and service.search.call_count == 1


def test_items_carry_no_private_data_over_http():
    http, _, _ = http_fixture(one_page())
    with http:
        response = http.get(URL)
    assert set(response.json()["items"][0]) == PUBLIC_FIELDS
    for marker in PRIVATE_MARKERS:
        assert marker not in response.text, marker


@pytest.mark.parametrize("query", [
    "unknown=1", "page=0", "page_size=51", "page=1&page=2", "q=",
    "skill_id=nope", "country_code=cm", "availability=weekly", "page=500&page_size=50",
])
def test_invalid_queries_are_rejected_after_the_quota(query):
    http, service, access = http_fixture()
    with http:
        response = http.get(f"{URL}?{query}")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"] and body["request_id"]
    assert response.headers["cache-control"] == "no-store"
    assert access.calls == [query] and service.search.call_count == 0


def test_body_on_search_is_refused():
    http, service, _ = http_fixture()
    with http:
        response = http.request("GET", URL, content=b'{"q":"a"}')
    assert response.status_code == 422 and service.search.call_count == 0


def test_mutations_on_the_search_route_are_not_allowed():
    http, service, _ = http_fixture()
    with http:
        for call in (http.post, http.put, http.delete, http.patch):
            assert call(URL).status_code == 405
    assert service.search.call_count == 0


def test_filters_reach_the_service_unchanged():
    http, service, _ = http_fixture()
    skill = "00000000-0000-4000-8000-000000000001"
    with http:
        http.get(f"{URL}?q=Ada&skill_id={skill}&city=Douala&country_code=CM"
                 "&availability=freelance&experience_level=senior&page=2&page_size=5")
    query = service.search.call_args.args[0]
    assert (query.q, query.city, query.country_code) == ("Ada", "Douala", "CM")
    assert [str(value) for value in query.skill_ids] == [skill]
    assert (query.availability, query.experience_level) == ("freelance", "senior")
    assert (query.page, query.page_size) == (2, 5)
