"""The transversal proof of http.md, end to end on real PostgreSQL.

One talent must never reach another's data, a valid session must not act without its
CSRF token, a revoked session must not act at all, and a coordinate marked private
must not appear to an anonymous visitor.
"""

import pytest

from tests.profiles.payloads import profile_payload
from tests.security.db_app import ORIGIN

pytestmark = pytest.mark.integration
ITEM = {"title": "Reel", "description": "", "type": "image"}


def as_account(http, account, csrf=True):
    http.cookies.clear()
    for name, value in account["cookies"].items():
        http.cookies.set(name, value)
    headers = {"Origin": ORIGIN, "Content-Type": "application/json"}
    if csrf:
        headers["X-CSRF-Token"] = str(account["csrf"])
    return headers


def own_item(http, account) -> str:
    headers = as_account(http, account)
    assert http.put("/api/v1/profiles/me", json=profile_payload(),
                    headers=headers).status_code in (200, 201)
    created = http.post("/api/v1/profiles/me/portfolio", json=ITEM, headers=headers)
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def test_another_owner_item_is_invisible_and_untouchable(live, two_sessions):
    owner, intruder = two_sessions
    item = own_item(live, owner)
    headers = as_account(live, intruder)
    for method, path in [
        ("get", f"/api/v1/profiles/me/portfolio/{item}"),
        ("delete", f"/api/v1/profiles/me/portfolio/{item}"),
        ("post", f"/api/v1/profiles/me/portfolio/{item}/publish"),
        ("post", f"/api/v1/profiles/me/portfolio/{item}/unpublish"),
    ]:
        response = getattr(live, method)(path, headers=headers)
        assert response.status_code == 404, (path, response.status_code)
        assert response.json()["error"]["code"] == "NOT_FOUND"
    # The owner still has it: nothing was deleted by the refused attempts.
    assert live.get(f"/api/v1/profiles/me/portfolio/{item}",
                    headers=as_account(live, owner)).status_code == 200


def test_a_session_cannot_act_without_its_csrf_token(live, two_sessions):
    owner = two_sessions[0]
    response = live.post("/api/v1/profiles/me/portfolio", json=ITEM,
                         headers=as_account(live, owner, csrf=False))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_a_revoked_session_is_refused(live, two_sessions):
    owner = two_sessions[0]
    headers = as_account(live, owner)
    assert live.post("/api/v1/auth/logout", headers=headers).status_code == 204
    response = live.get("/api/v1/auth/me", headers={"Origin": ORIGIN})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_owner_identifiers_sent_by_the_client_are_refused(live, two_sessions):
    owner, intruder = two_sessions
    payload = profile_payload() | {"user_id": "00000000-0000-4000-8000-000000000009"}
    response = live.put("/api/v1/profiles/me", json=payload, headers=as_account(live, owner))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_private_coordinates_never_reach_an_anonymous_visitor(live, two_sessions):
    owner = two_sessions[0]
    created = live.put("/api/v1/profiles/me", json=profile_payload(),
                       headers=as_account(live, owner))
    assert created.status_code in (200, 201)
    profile_id = str(created.json()["id"])
    live.cookies.clear()
    for path in [f"/api/v1/profiles/{profile_id}", f"/api/v1/profiles/{profile_id}/contacts"]:
        body = live.get(path).text
        assert "private@example.com" not in body, path
