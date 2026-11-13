"""The transport limit of http.md is the first control, ahead of everything else."""

GOOD = "https://diddifree.com"


def test_oversized_body_is_refused_before_anything_else(assembled):
    # This must not reach the database, which the fixture makes unreachable anyway.
    response = assembled.post("/api/v1/auth/register", headers={
        "Origin": GOOD, "X-Auth-Intent": "session", "Content-Type": "application/json",
    }, content=b'{"padding":"' + b"x" * 70000 + b'"}')
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "BODY_TOO_LARGE"
    assert response.headers["x-request-id"]


def test_a_non_json_body_is_refused_at_the_transport(assembled):
    response = assembled.post("/api/v1/profiles/me", headers={
        "Origin": GOOD, "Content-Type": "text/plain",
    }, content=b"not json")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert response.headers["x-request-id"]
