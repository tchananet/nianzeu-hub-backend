"""Header declaration for the published OpenAPI schema.

Every authenticated mutation requires ``X-CSRF-Token``, but FastAPI only documents a
header a route declares. Undeclared, the published schema hid a requirement the API
really has and the Swagger page offered no field to supply it, so "Try it out"
answered 403 with no way for the operator to fix it from the page.

This is documentation only: the token is read from the request and checked by the
identity service, so nothing here can reject a request the service would accept.
Declared optional on purpose -- required in the schema would make FastAPI answer 422
before the real check runs, which turns a precise CSRF refusal into a generic
validation error and rejects callers the service handles itself.
"""
from typing import Annotated

from fastapi import Header

CSRF = "Session CSRF token from `GET /api/v1/auth/csrf`. Required on every mutation."

CsrfToken = Annotated[str | None, Header(alias="X-CSRF-Token", description=CSRF)]


def declare_csrf(x_csrf_token: CsrfToken = None) -> None:
    """Publishes X-CSRF-Token. The value is checked by the identity service, not here."""
