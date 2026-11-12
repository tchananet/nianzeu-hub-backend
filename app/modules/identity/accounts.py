from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.primitives import Clock, utc_now
from app.modules.identity.models import Credential, User
from app.modules.identity.passwords import Passwords
from app.modules.identity.schemas import CredentialsInput, UserDTO
from app.shared.errors import AppError, EmailUnavailable


def public_user(user: User) -> UserDTO:
    return UserDTO(id=user.id, email=user.email, created_at=user.created_at)


def register(
    db: Session, data: CredentialsInput, passwords: Passwords, clock: Clock = utc_now,
) -> UserDTO:
    now, user_id = clock(), uuid4()
    encoded = passwords.hash(data.password)
    inserted = db.execute(
        insert(User).values(id=user_id, email=data.email, role="talent", is_active=True,
                            created_at=now, updated_at=now)
        .on_conflict_do_nothing(index_elements=[User.email]).returning(User.id)
    ).scalar_one_or_none()
    if inserted is None:
        raise AppError("EMAIL_UNAVAILABLE", 409, "Email unavailable")
    db.add(Credential(user_id=user_id, password_hash=encoded, updated_at=now))
    db.flush()
    return UserDTO(id=user_id, email=data.email, created_at=now)


def authenticate(
    db: Session, data: CredentialsInput, passwords: Passwords, clock: Clock = utc_now,
) -> User:
    user = db.scalar(select(User).where(User.email == data.email).with_for_update())
    credential = db.get(Credential, user.id) if user is not None else None
    encoded = credential.password_hash if credential is not None else None
    verified = passwords.verify(encoded, data.password)
    if not verified or user is None or not user.is_active or credential is None:
        raise AppError("INVALID_CREDENTIALS", 401, "Invalid credentials")
    if passwords.needs_rehash(credential.password_hash):
        credential.password_hash = passwords.hash(data.password)
        credential.updated_at = clock()
    return user


def unavailable_reset() -> None:
    """No account lookup, token write or provider invocation, including unknown emails."""
    raise EmailUnavailable()
