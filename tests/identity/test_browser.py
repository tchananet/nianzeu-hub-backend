import pytest
from fastapi import Request, Response

from app.core.config import Settings
from app.modules.identity.browser import BrowserPolicy
from app.shared.errors import AppError


def policy(cross_site: bool = True, secure: bool = True,
           frontend: str = "https://app.example.com") -> BrowserPolicy:
    return BrowserPolicy(Settings.model_construct(
        environment="test", session_cross_site_enabled=cross_site, secure_cookies=secure,
        frontend_origin=frontend,
    ))


def request(headers: dict[str, str], path: str = "/api/v1/auth/login") -> Request:
    return Request({"type": "http", "method": "POST", "path": path,
                    "headers": [(k.encode(), v.encode()) for k, v in headers.items()]})


def test_cross_site_requires_an_origin() -> None:
    browser = policy()
    headers = {"origin": "http://localhost:5173", "sec-fetch-site": "cross-site",
               "content-type": "application/json"}
    browser.validate_mutation(request(headers))
    # No custom header is demanded: the origin and the JSON content type already
    # refuse a cross-site form post, so a fourth lock bought nothing.
    with pytest.raises(AppError):
        browser.validate_mutation(request({k: v for k, v in headers.items() if k != "origin"}))
    with pytest.raises(AppError):
        policy(False).validate_mutation(request(headers))
    with pytest.raises(AppError):
        browser.validate_auth_read(request({}))


def test_cookie_and_deletion_attributes() -> None:
    browser, response = policy(), Response()
    browser.set_cookie(response, "opaque")
    cookie = response.headers["set-cookie"]
    for attribute in ["__Host-session=opaque", "Secure", "HttpOnly", "SameSite=none",
                      "Path=/", "Max-Age=604800"]:
        assert attribute in cookie
    assert "Domain=" not in cookie
    response = Response()
    browser.expire_cookie(response)
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "SameSite=none" in response.headers["set-cookie"]
    assert policy(False, False).cookie_name == "session_local"


def test_duplicate_origin_rejected() -> None:
    value = request({"origin": "https://diddifree.com"})
    value.scope["headers"].append((b"origin", b"https://netatroniks.xyz"))
    with pytest.raises(AppError):
        policy().validate_origin(value, required=True)
