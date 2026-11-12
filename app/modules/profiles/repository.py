from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.identity.models import User
from app.modules.profiles.models import Profile
from app.shared.errors import AppError, DependencyUnavailable


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    try:
        with factory.begin() as db:
            yield db
    except SQLAlchemyError:
        raise DependencyUnavailable() from None


def lock_user(db: Session, user_id: UUID) -> None:
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or not user.is_active:
        raise AppError("AUTH_REQUIRED", 401, "Authentication required")


def own_profile(db: Session, user_id: UUID, write: bool = False) -> Profile:
    if write:
        lock_user(db, user_id)
    row = db.scalar(select(Profile).where(Profile.user_id == user_id)
                    .with_for_update(read=not write))
    if row is None:
        raise AppError("NOT_FOUND", 404, "Profile not found")
    return row


def public_profile(db: Session, profile_id: UUID) -> Profile:
    row = db.scalar(select(Profile).where(Profile.id == profile_id).with_for_update(read=True))
    if row is None:
        raise AppError("NOT_FOUND", 404, "Profile not found")
    return row
