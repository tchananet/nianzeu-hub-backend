from fastapi import APIRouter, Request, Response

from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.modules.identity.schemas import CsrfResponse, UserResponse
from app.modules.identity.service import Authenticated, IdentityService
from app.modules.identity.validation import reject_query


def private_router(service: IdentityService, limits: IdentityLimits,
                   browser: BrowserPolicy) -> APIRouter:
    router = APIRouter()

    def identity(request: Request, response: Response, mutation: bool = False) -> Authenticated:
        response.headers.update({"Cache-Control": "no-store", "Vary": "Origin"})
        if mutation:
            browser.validate_mutation(request)
        else:
            browser.validate_auth_read(request)
        result = service.authenticate(browser.read_token(request),
                                      request.headers.get("X-CSRF-Token"), mutation)
        limits.user(result.principal.user_id, mutation)
        reject_query(request)
        return result

    @router.get("/me")
    def me(request: Request, response: Response) -> UserResponse:
        return UserResponse(user=identity(request, response).user)

    @router.get("/csrf")
    def csrf(request: Request, response: Response) -> CsrfResponse:
        browser.validate_csrf_read(request)
        return CsrfResponse(csrf_token=identity(request, response).csrf_token)

    @router.post("/logout", status_code=204, response_class=Response)
    def logout(request: Request) -> Response:
        response = Response(status_code=204)
        identity(request, response, mutation=True)
        service.logout(browser.read_token(request), request.headers.get("X-CSRF-Token"))
        browser.expire_cookie(response)
        return response

    return router
