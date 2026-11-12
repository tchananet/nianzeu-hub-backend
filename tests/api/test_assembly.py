"""X01: every contract route is actually mounted on the assembled application.

A route that is not mounted answers 404, and a path mounted under another method
answers 405. A mounted private route reached without a session answers either 401,
when the session check runs first, or 503, when the per-IP quota of http.md runs
first and cannot reach the database. So "neither 404 nor 405, in the enveloped
error shape" is exactly the proof that the route is wired, with no database.
"""

from uuid import uuid4

import pytest

ID = str(uuid4())
PRIVATE = [
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/auth/csrf"),
    ("post", "/api/v1/auth/logout"),
    ("get", "/api/v1/profiles/me"),
    ("put", "/api/v1/profiles/me"),
    ("delete", "/api/v1/profiles/me"),
    ("get", "/api/v1/profiles/me/contacts"),
    ("put", "/api/v1/profiles/me/contacts"),
    ("get", "/api/v1/profiles/me/portfolio"),
    ("post", "/api/v1/profiles/me/portfolio"),
    ("post", "/api/v1/profiles/me/portfolio/upload-url"),
    ("get", f"/api/v1/profiles/me/portfolio/{ID}"),
    ("delete", f"/api/v1/profiles/me/portfolio/{ID}"),
    ("post", f"/api/v1/profiles/me/portfolio/{ID}/validate"),
    ("post", f"/api/v1/profiles/me/portfolio/{ID}/publish"),
    ("post", f"/api/v1/profiles/me/portfolio/{ID}/unpublish"),
]


PUBLIC = [
    ("get", "/api/v1/skills"),
    ("get", "/api/v1/search/profiles"),
    ("get", f"/api/v1/profiles/{ID}"),
    ("get", f"/api/v1/profiles/{ID}/contacts"),
    ("get", f"/api/v1/profiles/{ID}/portfolio"),
    ("get", f"/api/v1/portfolio/{ID}/content"),
    ("post", f"/api/v1/profiles/{ID}/views"),
]


@pytest.mark.parametrize(("method", "path"), PUBLIC)
def test_public_routes_are_mounted_and_need_no_session(assembled, method, path):
    response = getattr(assembled, method)(path, headers={"Origin": "https://diddifree.com"})
    assert response.status_code not in (404, 405), f"{path} is not mounted"
    # Anonymous access is allowed, so these never demand a session; they stop at the
    # shared public quota, which this fixture makes unreachable.
    assert response.status_code != 401, path
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"


@pytest.mark.parametrize(("method", "path"), PRIVATE)
def test_private_routes_are_mounted_and_refuse_anonymous_access(assembled, method, path):
    response = getattr(assembled, method)(path, headers={"Origin": "https://diddifree.com"})
    assert response.status_code not in (404, 405), f"{path} is not mounted"
    assert response.status_code in (401, 403, 503), (path, response.status_code)
    body = response.json()
    assert body["error"]["code"] in {"AUTH_REQUIRED", "CSRF_FAILED", "DEPENDENCY_UNAVAILABLE"}
    assert body["error"]["details"] == []
    assert body["request_id"] == response.headers["x-request-id"]


def test_unknown_route_is_a_framework_free_envelope(assembled):
    response = assembled.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_unknown_method_reports_allow(assembled):
    response = assembled.delete("/api/v1/auth/login")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "POST" in response.headers["allow"]


def test_health_stays_outside_the_versioned_api(assembled):
    assert assembled.get("/health/live").json() == {"status": "ok"}
