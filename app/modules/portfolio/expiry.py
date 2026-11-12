from datetime import datetime

from sqlalchemy import select
from sqlalchemy.sql import Select

from app.modules.portfolio import states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.lease import reject_rows
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
from app.modules.portfolio.repository import transaction

EXPIRY_BATCH = 200


def pairs() -> Select[tuple[PortfolioItem, PortfolioUpload]]:
    return select(PortfolioItem, PortfolioUpload).join(
        PortfolioUpload, PortfolioUpload.item_id == PortfolioItem.id
    )


def mark(context: PortfolioContext, statement: Select[tuple[PortfolioItem, PortfolioUpload]],
         code: str, now: datetime) -> int:
    with transaction(context.factory) as db:
        rows = db.execute(statement.with_for_update().limit(EXPIRY_BATCH)).all()
        for item, upload in rows:
            reject_rows(item, upload, code, now)
        db.flush()
        return len(rows)


def expire_reservations(context: PortfolioContext, now: datetime) -> int:
    """Stale pending uploads become rejected and give their reserved bytes back."""
    return mark(
        context,
        pairs().where(
            PortfolioUpload.expires_at <= now,
            PortfolioUpload.reservation_active.is_(True),
            PortfolioItem.state == states.PENDING,
        ),
        "UPLOAD_EXPIRED",
        now,
    )


def expire_leases(context: PortfolioContext, now: datetime) -> int:
    """Validations abandoned past their lease are rejected rather than left stuck."""
    return mark(
        context,
        pairs().where(
            PortfolioItem.state == states.VALIDATING,
            PortfolioUpload.lease_until.is_not(None),
            PortfolioUpload.lease_until <= now,
        ),
        "LEASE_EXPIRED",
        now,
    )
