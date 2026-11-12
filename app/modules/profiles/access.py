from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, ip_quota_key, utc_now
from app.core.quotas import consume
from app.modules.identity.browser import BrowserPolicy
from app.modules.identity.limits import IdentityLimits
from app.shared.errors import DependencyUnavailable
from app.shared.principal import Principal, PrincipalResolver


class ProfileAccess:
    def __init__(self, resolver: PrincipalResolver, browser: BrowserPolicy,
                 factory: sessionmaker[Session], secret: str, clock: Clock = utc_now) -> None:
        self.resolver, self.browser, self.factory = resolver, browser, factory
        self.secret, self.clock = secret, clock
        self.limits = IdentityLimits(factory, secret, clock)

    def owner(self, request: Request, response: Response) -> Principal:
        principal = self.resolver(request)
        self.limits.user(principal.user_id, request.method not in {"GET", "HEAD"})
        no_query(request)
        private_headers(response)
        return principal

    def public(self, request: Request, response: Response) -> None:
        self.public_limit(request)
        no_query(request)
        private_headers(response)

    def public_limit(self, request: Request) -> None:
        consume(self.factory, "public_json", self.visitor(request), 120, 60, self.clock)

    def view(self, request: Request, response: Response) -> str:
        self.browser.validate_mutation(request)
        key = self.visitor(request)
        consume(self.factory, "profile_views", key, 30, 60, self.clock)
        no_query(request)
        private_headers(response)
        return key

    def visitor(self, request: Request) -> str:
        if request.client is None:
            raise DependencyUnavailable()
        return ip_quota_key(self.secret, request.client.host)


def no_query(request: Request) -> None:
    if request.query_params:
        raise RequestValidationError([{"loc": ("query", key), "type": "value_error"}
                                      for key in request.query_params])


def private_headers(response: Response) -> None:
    response.headers.update({"Cache-Control": "no-store", "Vary": "Origin"})
