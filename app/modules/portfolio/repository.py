from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.identity.models import User
from app.modules.portfolio import states
from app.modules.portfolio.errors import not_found, profile_required
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
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
    """Owner-wide lock: quotas are recomputed from rows, never from a counter."""
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None or not user.is_active:
        raise AppError("AUTH_REQUIRED", 401, "Authentication required")


def profile_id_of(db: Session, user_id: UUID, lock: bool = False) -> UUID | None:
    if lock:
        lock_user(db, user_id)
    return db.scalar(select(Profile.id).where(Profile.user_id == user_id))


def required_profile_id(db: Session, user_id: UUID, lock: bool = False) -> UUID:
    """Creation and upload reservation demand an existing profile (409)."""
    profile_id = profile_id_of(db, user_id, lock)
    if profile_id is None:
        raise profile_required()
    return profile_id


def owning_profile_id(db: Session, user_id: UUID, lock: bool = False) -> UUID:
    """Item-scoped routes cannot reveal whether the profile or the item is missing (404)."""
    profile_id = profile_id_of(db, user_id, lock)
    if profile_id is None:
        raise not_found()
    return profile_id


def existing_profile(db: Session, profile_id: UUID) -> UUID:
    found = db.scalar(select(Profile.id).where(Profile.id == profile_id))
    if found is None:
        raise not_found()
    return found


def own_item(db: Session, profile_id: UUID, item_id: UUID, write: bool = False) -> PortfolioItem:
    item = db.scalar(
        select(PortfolioItem)
        .where(PortfolioItem.id == item_id, PortfolioItem.profile_id == profile_id)
        .with_for_update(read=not write)
    )
    if item is None:
        raise not_found()
    return item


def current_upload(db: Session, item_id: UUID, write: bool = False) -> PortfolioUpload | None:
    return db.scalar(
        select(PortfolioUpload)
        .where(PortfolioUpload.item_id == item_id)
        .with_for_update(read=not write)
    )


def published_item(db: Session, item_id: UUID) -> PortfolioItem:
    item = db.scalar(
        select(PortfolioItem).where(
            PortfolioItem.id == item_id, PortfolioItem.state == states.PUBLISHED
        )
    )
    if item is None:
        raise not_found()
    return item
