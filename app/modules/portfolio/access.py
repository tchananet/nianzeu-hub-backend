from fastapi import Request, Response
from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, ip_quota_key, quota_key, utc_now
from app.core.quotas import consume
from app.modules.identity.limits import IdentityLimits
from app.modules.profiles.access import no_query, private_headers
from app.shared.errors import DependencyUnavailable
from app.shared.principal import Principal, PrincipalResolver

ROUTE_LIMIT = (10, 3600)


class PortfolioAccess:
    """Session, CSRF and Origin come from the identity resolver; quotas are atomic in DB."""

    def __init__(
        self,
        resolver: PrincipalResolver,
        factory: sessionmaker[Session],
        secret: str,
        clock: Clock = utc_now,
    ) -> None:
        self.resolver, self.factory = resolver, factory
        self.secret, self.clock = secret, clock
        self.limits = IdentityLimits(factory, secret, clock)

    def collection(self, request: Request, response: Response) -> Principal:
        """Paginated owner routes: the pagination dependency owns the query allowlist."""
        principal = self.resolver(request)
        self.limits.user(principal.user_id, request.method not in {"GET", "HEAD"})
        private_headers(response)
        return principal

    def owner(self, request: Request, response: Response) -> Principal:
        principal = self.collection(request, response)
        no_query(request)
        return principal

    def upload_url(self, request: Request, response: Response) -> Principal:
        return self.route_limited(request, response, "portfolio_upload_url")

    def validate(self, request: Request, response: Response) -> Principal:
        return self.route_limited(request, response, "portfolio_validate")

    def route_limited(self, request: Request, response: Response, scope: str) -> Principal:
        principal = self.owner(request, response)
        limit, seconds = ROUTE_LIMIT
        consume(
            self.factory, scope, quota_key(self.secret, str(principal.user_id)),
            limit, seconds, self.clock,
        )
        return principal

    def public(self, request: Request, response: Response) -> None:
        consume(self.factory, "public_json", self.visitor(request), 120, 60, self.clock)
        private_headers(response)

    def content(self, request: Request) -> None:
        consume(self.factory, "file_content", self.visitor(request), 60, 60, self.clock)
        no_query(request)

    def visitor(self, request: Request) -> str:
        if request.client is None:
            raise DependencyUnavailable()
        return ip_quota_key(self.secret, request.client.host)
