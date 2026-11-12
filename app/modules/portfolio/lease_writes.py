from app.modules.portfolio import projections, states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.errors import invalid_state, not_found
from app.modules.portfolio.lease import Lease, held, locked_rows, reject_rows
from app.modules.portfolio.repository import transaction
from app.modules.portfolio.responses import ItemOwner


def release(context: PortfolioContext, lease: Lease) -> None:
    """Storage failure or absent object: back to pending, reservation kept for a retry."""
    now = context.clock()
    with transaction(context.factory) as db:
        item, upload = locked_rows(db, lease.item_id)
        if not held(item, upload, lease) or item is None or upload is None:
            return
        item.state = states.PENDING
        item.updated_at = now
        upload.lease_until = None
        db.flush()


def reject(context: PortfolioContext, lease: Lease, code: str) -> None:
    now = context.clock()
    with transaction(context.factory) as db:
        item, upload = locked_rows(db, lease.item_id)
        if not held(item, upload, lease) or item is None or upload is None:
            return
        reject_rows(item, upload, code, now)
        db.flush()


def finalize(context: PortfolioContext, lease: Lease, object_key: str, digest: str) -> ItemOwner:
    """Commits validated state only while lease, upload, item and profile still exist."""
    now = context.clock()
    with transaction(context.factory) as db:
        item, upload = locked_rows(db, lease.item_id)
        if item is None:
            raise not_found()
        if not held(item, upload, lease) or upload is None:
            raise invalid_state()
        item.state = states.VALIDATED
        item.validated_at = now
        item.updated_at = now
        item.object_key = object_key
        item.filename = upload.filename
        item.media_type = upload.media_type
        item.size_bytes = upload.size_bytes
        item.sha256 = digest
        item.rejection_code = None
        upload.reservation_active = False
        upload.lease_until = None
        db.flush()
        return projections.owner(item)
