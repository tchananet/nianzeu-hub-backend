from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, Response

from app.modules.identity.accounts import unavailable_reset
from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.modules.identity.private_routes import private_router
from app.modules.identity.schemas import (
    CredentialsInput,
    EmailInput,
    LoginResponse,
    ResetInput,
    UserResponse,
)
from app.modules.identity.service import IdentityService
from app.modules.identity.validation import reject_query
from app.shared.errors import DependencyUnavailable


def create_router(service: IdentityService, limits: IdentityLimits,
                  browser: BrowserPolicy) -> APIRouter:
    def guard(group: str) -> Callable[[Request, Response], None]:
        def check(request: Request, response: Response) -> None:
            response.headers.update({"Cache-Control": "no-store", "Vary": "Origin"})
            browser.validate_mutation(request)
            if request.client is None:
                raise DependencyUnavailable()
            limits.ip(group, request.client.host)
            reject_query(request)
        return check

    router = APIRouter(prefix="/api/v1/auth")

    @router.post("/register", status_code=201, dependencies=[Depends(guard("register"))])
    def register(data: CredentialsInput) -> UserResponse:
        return UserResponse(user=service.register(data))

    @router.post("/login", dependencies=[Depends(guard("login"))])
    def login(data: CredentialsInput, request: Request, response: Response) -> LoginResponse:
        limits.login_email(data.email)
        result = service.login(
            data, browser.read_token(request), request.headers.get("X-CSRF-Token"))
        browser.set_cookie(response, result.token)
        return LoginResponse(user=result.identity.user, csrf_token=result.identity.csrf_token)

    @router.post("/password/forgot", dependencies=[Depends(guard("reset"))])
    def forgot(data: EmailInput) -> None:
        unavailable_reset()

    @router.post("/password/reset", dependencies=[Depends(guard("reset"))])
    def reset(data: ResetInput) -> None:
        unavailable_reset()

    router.include_router(private_router(service, limits, browser))
    return router
