"""Origin and intent are refused before anything touches the database.

The fixture makes every database connection fail, so a 503 would mean the request
reached the quota counter. Getting 403 or 415 instead is positive proof that the
transport and Origin checks of http.md run first, as its control order requires.
"""

import pytest

GOOD = "https://diddifree.com"
MUTATIONS = [
    ("post", "/api/v1/auth/register"),
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/auth/logout"),
    ("put", "/api/v1/profiles/me"),
    ("delete", "/api/v1/profiles/me"),
    ("put", "/api/v1/profiles/me/contacts"),
    ("post", "/api/v1/profiles/me/portfolio"),
]
LOGIN_LIKE = ["/api/v1/auth/register", "/api/v1/auth/login"]
INTENT = {"X-Auth-Intent": "session", "Content-Type": "application/json"}


def forbidden(response, code: str) -> None:
    assert response.status_code == 403, response.status_code
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["details"] == []


@pytest.mark.parametrize(("method", "path"), MUTATIONS)
def test_mutation_without_origin_is_refused_before_the_database(assembled, method, path):
    forbidden(getattr(assembled, method)(path, headers=INTENT), "ORIGIN_FORBIDDEN")


@pytest.mark.parametrize(("method", "path"), MUTATIONS)
def test_mutation_from_a_foreign_origin_is_refused(assembled, method, path):
    headers = dict(INTENT, Origin="https://evil.example")
    forbidden(getattr(assembled, method)(path, headers=headers), "ORIGIN_FORBIDDEN")


@pytest.mark.parametrize(("method", "path"), MUTATIONS)
def test_cross_site_fetch_metadata_is_refused(assembled, method, path):
    headers = dict(INTENT, Origin=GOOD)
    headers["Sec-Fetch-Site"] = "cross-site"
    forbidden(getattr(assembled, method)(path, headers=headers), "ORIGIN_FORBIDDEN")


def test_duplicate_origin_headers_are_refused(assembled):
    # httpx keeps repeated headers, which is exactly the ambiguity the policy rejects.
    headers = [("origin", GOOD), ("origin", GOOD), ("x-auth-intent", "session"),
               ("content-type", "application/json")]
    forbidden(assembled.post("/api/v1/auth/login", headers=headers), "ORIGIN_FORBIDDEN")


@pytest.mark.parametrize("path", LOGIN_LIKE)
def test_credential_routes_demand_an_explicit_session_intent(assembled, path):
    headers = {"Origin": GOOD, "Content-Type": "application/json"}
    forbidden(assembled.post(path, headers=headers), "CSRF_FAILED")


@pytest.mark.parametrize("path", LOGIN_LIKE)
def test_credential_routes_reject_a_form_content_type(assembled, path):
    # A form post is how a cross-site page would try to submit credentials.
    headers = {"Origin": GOOD, "X-Auth-Intent": "session",
               "Content-Type": "application/x-www-form-urlencoded"}
    response = assembled.post(path, headers=headers, content="email=a@b.c&password=x")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
