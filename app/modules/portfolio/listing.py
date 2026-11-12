from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.portfolio import projections, states
from app.modules.portfolio.models import PortfolioItem
from app.modules.portfolio.responses import ItemOwner, ItemPublic
from app.shared.dto import Page, Pagination


def owner_page(db: Session, profile_id: UUID, query: Pagination) -> Page[ItemOwner]:
    statement = select(PortfolioItem).where(PortfolioItem.profile_id == profile_id)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(PortfolioItem.created_at.desc(), PortfolioItem.id.asc())
        .offset(query.offset)
        .limit(query.page_size)
    )
    return Page[ItemOwner](
        items=[projections.owner(row) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )


def public_page(db: Session, profile_id: UUID, query: Pagination) -> Page[ItemPublic]:
    statement = select(PortfolioItem).where(
        PortfolioItem.profile_id == profile_id, PortfolioItem.state == states.PUBLISHED
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(PortfolioItem.published_at.desc(), PortfolioItem.id.asc())
        .offset(query.offset)
        .limit(query.page_size)
    )
    return Page[ItemPublic](
        items=[projections.public(row) for row in rows],
        page=query.page,
        page_size=query.page_size,
        total=total,
    )
