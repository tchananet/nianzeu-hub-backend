from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.portfolio import states
from app.modules.portfolio.errors import quota_exceeded
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload


def used_items(db: Session, profile_id: UUID) -> int:
    total = db.scalar(
        select(func.count()).select_from(PortfolioItem).where(
            PortfolioItem.profile_id == profile_id
        )
    )
    return total or 0


def used_bytes(db: Session, profile_id: UUID) -> int:
    """Validated/published files plus every active reservation of this owner."""
    stored = db.scalar(
        select(func.coalesce(func.sum(PortfolioItem.size_bytes), 0)).where(
            PortfolioItem.profile_id == profile_id,
            PortfolioItem.state.in_(states.FINAL_FILE),
        )
    )
    reserved = db.scalar(
        select(func.coalesce(func.sum(PortfolioUpload.size_bytes), 0))
        .join(PortfolioItem, PortfolioItem.id == PortfolioUpload.item_id)
        .where(
            PortfolioItem.profile_id == profile_id,
            PortfolioUpload.reservation_active.is_(True),
        )
    )
    return int(stored or 0) + int(reserved or 0)


def require_item_slot(db: Session, profile_id: UUID) -> None:
    if used_items(db, profile_id) >= states.ITEM_QUOTA:
        raise quota_exceeded()


def require_bytes(db: Session, profile_id: UUID, size_bytes: int) -> None:
    if used_bytes(db, profile_id) + size_bytes > states.BYTE_QUOTA:
        raise quota_exceeded()
