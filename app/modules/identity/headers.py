"""Header declarations for the published OpenAPI schema.

``BrowserPolicy`` enforces these two headers, but FastAPI only learns about a header
when a route declares it. Without a declaration the schema hid requirements the API
really has, and the Swagger page offered no field to supply them -- so "Try it out"
on login and register answered 403 with no way for the operator to fix it from the
page. These are documentation only: enforcement stays in one place, so nothing here
can reject a request the policy would have accepted.

Declared optional on purpose. Marking them required would make FastAPI answer 422
before the policy runs, which would break direct clients in open mode -- where no
origin is configured and the policy deliberately asks for neither header.
"""
from typing import Annotated

from fastapi import Header

INTENT = "Must be `session`. Required on login and register when an origin is configured."
CSRF = "Session CSRF token from `GET /api/v1/auth/csrf`. Required on every mutation."

AuthIntent = Annotated[str | None, Header(alias="X-Auth-Intent", description=INTENT)]
CsrfToken = Annotated[str | None, Header(alias="X-CSRF-Token", description=CSRF)]


def declare_intent(x_auth_intent: AuthIntent = None) -> None:
    """Publishes X-Auth-Intent. The value is checked by BrowserPolicy, not here."""


def declare_csrf(x_csrf_token: CsrfToken = None) -> None:
    """Publishes X-CSRF-Token. The value is checked by the identity service, not here."""
