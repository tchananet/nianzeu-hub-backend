from fastapi import Request

from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.service import IdentityService
from app.shared.principal import Principal


class IdentityPrincipalResolver:
    def __init__(self, service: IdentityService, browser: BrowserPolicy) -> None:
        self.service, self.browser = service, browser

    def __call__(self, request: Request) -> Principal:
        mutation = request.method not in {"GET", "HEAD", "OPTIONS"}
        if mutation:
            self.browser.validate_mutation(request)
        result = self.service.authenticate(
            self.browser.read_token(request), request.headers.get("X-CSRF-Token"), mutation,
        )
        return result.principal
