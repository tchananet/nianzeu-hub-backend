from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.primitives import Clock, utc_now
from app.modules.identity import accounts, sessions
from app.modules.identity.login_security import lock_login
from app.modules.identity.passwords import Passwords
from app.modules.identity.schemas import CredentialsInput, UserDTO
from app.shared.errors import DependencyUnavailable
from app.shared.principal import Principal


@dataclass(frozen=True)
class Authenticated:
    user: UserDTO
    principal: Principal
    csrf_token: str = field(repr=False)


@dataclass(frozen=True)
class LoginResult:
    identity: Authenticated
    token: str = field(repr=False)


class IdentityService:
    def __init__(self, factory: sessionmaker[Session], passwords: Passwords,
                 clock: Clock = utc_now) -> None:
        self.factory, self.passwords, self.clock = factory, passwords, clock

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        try:
            with self.factory.begin() as db:
                yield db
        except SQLAlchemyError:
            raise DependencyUnavailable() from None

    def register(self, data: CredentialsInput) -> UserDTO:
        with self.transaction() as db:
            return accounts.register(db, data, self.passwords, self.clock)

    def login(self, data: CredentialsInput, previous: str | None = None,
              csrf: str | None = None) -> LoginResult:
        with self.transaction() as db:
            old = lock_login(db, data.email, previous, csrf, self.clock())
            user = accounts.authenticate(db, data, self.passwords, self.clock)
            now = self.clock()
            if old is not None:
                old.revoked_at = now
            row, token = sessions.issue(db, user, now)
            identity = Authenticated(accounts.public_user(user), Principal(user.id, row.id),
                                     row.csrf_token)
            return LoginResult(identity, token)

    def authenticate(self, token: str | None, csrf: str | None = None,
                     mutation: bool = False) -> Authenticated:
        with self.transaction() as db:
            user, row = sessions.resolve(db, token, self.clock())
            if mutation:
                sessions.check_csrf(row, csrf)
            return Authenticated(accounts.public_user(user), Principal(user.id, row.id),
                                 row.csrf_token)

    def logout(self, token: str | None, csrf: str | None) -> None:
        with self.transaction() as db:
            _, row = sessions.resolve(db, token, self.clock())
            sessions.check_csrf(row, csrf)
            row.revoked_at = self.clock()
