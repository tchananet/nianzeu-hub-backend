from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import Request, Response

from app.modules.profiles.access import ProfileAccess
from app.shared.errors import AppError
from app.shared.principal import Principal


def request(method="GET", query=b""):
    return Request({"type": "http", "method": method, "query_string": query,
                    "headers": [], "client": ("127.0.0.1", 1000)})


def test_owner_quota_and_origin_failure_before_view_side_effect():
    principal = Principal(uuid4(), uuid4())
    resolver, browser = Mock(return_value=principal), Mock()
    access = ProfileAccess(resolver, browser, Mock(), "x" * 32)
    access.limits = Mock()
    response = Response()
    assert access.owner(request("PUT"), response) == principal
    access.limits.user.assert_called_once_with(principal.user_id, True)
    assert response.headers["cache-control"] == "no-store"
    resolver.side_effect = AppError("CSRF_FAILED", 403)
    access.limits.reset_mock()
    with pytest.raises(AppError):
        access.owner(request("PUT"), Response())
    access.limits.user.assert_not_called()
    browser.validate_mutation.side_effect = AppError("ORIGIN_FORBIDDEN", 403)
    with patch("app.modules.profiles.access.consume") as consume:
        with pytest.raises(AppError):
            access.view(request("POST"), response)
        consume.assert_not_called()


def test_shared_public_quota_and_hashed_visitors():
    access = ProfileAccess(Mock(), Mock(), Mock(), "x" * 32)
    with patch("app.modules.profiles.access.consume") as consume:
        access.public(request(), Response())
        args = consume.call_args.args
        assert args[1] == "public_json" and args[3:5] == (120, 60)
        assert len(args[2]) == 64 and "127.0.0.1" not in args[2]
