from tests.profiles.http_fixture import http_fixture
from tests.profiles.payloads import profile_payload


def test_profile_owner_routes_and_location():
    http, service, contacts, views, owner = http_fixture()
    with http:
        response = http.put("/api/v1/profiles/me", json=profile_payload())
        assert response.status_code == 201
        assert response.headers["location"] == f"/api/v1/profiles/{owner.id}"
        assert response.headers["cache-control"] == "no-store"
        service.put.return_value = owner, False
        assert http.put("/api/v1/profiles/me", json=profile_payload()).status_code == 200
        assert http.get("/api/v1/profiles/me").status_code == 200
        assert http.get("/api/v1/profiles/me?user_id=other").status_code == 422
        assert http.get("/api/v1/profiles/me/contacts").status_code == 200
        assert http.put("/api/v1/profiles/me/contacts",
                        json=profile_payload()["contacts"]).status_code == 200
        assert http.delete("/api/v1/profiles/me").status_code == 204
        assert http.post(f"/api/v1/profiles/{owner.id}/views").status_code == 204
        views.record.assert_called_once_with(owner.id, "a" * 64)
        service.delete.assert_called_once_with(owner.user_id)
        contacts.put.assert_called_once()


def test_unknown_fields_and_no_body_routes_do_not_write():
    http, service, _, views, owner = http_fixture()
    with http:
        response = http.put("/api/v1/profiles/me", json={**profile_payload(), "user_id": "other"})
        assert response.status_code == 422
        response = http.post(f"/api/v1/profiles/{owner.id}/views", json={"count": 100})
        assert response.status_code == 422
        assert http.put(f"/api/v1/profiles/{owner.id}", json=profile_payload()).status_code == 405
        service.put.assert_not_called()
        views.record.assert_not_called()
