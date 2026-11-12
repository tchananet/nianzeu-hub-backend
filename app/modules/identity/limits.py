from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, ip_quota_key, quota_key, utc_now
from app.core.quotas import consume, purge_expired


class IdentityLimits:
    def __init__(self, factory: sessionmaker[Session], secret: str,
                 clock: Clock = utc_now) -> None:
        self.factory, self.secret, self.clock = factory, secret, clock

    def ip(self, group: str, address: str) -> None:
        limits = {"register": (5, 3600), "login": (30, 900), "reset": (5, 3600)}
        limit, seconds = limits[group]
        consume(self.factory, f"identity_{group}_ip", ip_quota_key(self.secret, address),
                limit, seconds, self.clock)

    def login_email(self, email: str) -> None:
        consume(self.factory, "identity_login_email", quota_key(self.secret, email),
                10, 900, self.clock)

    def user(self, user_id: UUID, mutation: bool = False) -> None:
        scope, limit = ("private_mutations", 60) if mutation else ("private_reads", 120)
        consume(self.factory, scope, quota_key(self.secret, str(user_id)), limit, 60, self.clock)

    def purge(self) -> int:
        return purge_expired(self.factory, self.clock)
