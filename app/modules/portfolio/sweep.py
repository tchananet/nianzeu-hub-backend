from datetime import datetime

from sqlalchemy import select

from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.keys import FINAL_PREFIX, QUARANTINE_PREFIX
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
from app.modules.portfolio.repository import transaction
from app.modules.portfolio.storage import SweepPort
from app.modules.portfolio.store_cleanup import drop_objects

SWEEP_BATCH = 500


def candidates(sweep: SweepPort | None, bucket: str, prefix: str, cutoff: datetime) -> list[str]:
    if sweep is None:
        return []
    found: list[str] = []
    for key, modified in sweep.list_keys(bucket, prefix):
        if modified <= cutoff:
            found.append(key)
        if len(found) >= SWEEP_BATCH:
            break
    return found


def sweep_quarantine(context: PortfolioContext, sweep: SweepPort | None, cutoff: datetime) -> int:
    """Quarantine objects older than the cutoff go once the database confirms no reservation."""
    bucket = context.quarantine_bucket
    keys = candidates(sweep, bucket, QUARANTINE_PREFIX, cutoff)
    if not keys:
        return 0
    with transaction(context.factory) as db:
        live = set(
            db.scalars(
                select(PortfolioUpload.quarantine_key).where(
                    PortfolioUpload.quarantine_key.in_(keys),
                    PortfolioUpload.reservation_active.is_(True),
                )
            )
        )
    return drop_objects(context.storage, bucket, [key for key in keys if key not in live])


def sweep_final(context: PortfolioContext, sweep: SweepPort | None, cutoff: datetime) -> int:
    """Final objects are removed only when no item references them any more."""
    bucket = context.validated_bucket
    keys = candidates(sweep, bucket, FINAL_PREFIX, cutoff)
    if not keys:
        return 0
    with transaction(context.factory) as db:
        live = set(
            db.scalars(select(PortfolioItem.object_key).where(PortfolioItem.object_key.in_(keys)))
        )
    return drop_objects(context.storage, bucket, [key for key in keys if key not in live])
