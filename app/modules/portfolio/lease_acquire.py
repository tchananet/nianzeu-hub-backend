from datetime import datetime, timedelta
from uuid import UUID

from app.modules.portfolio import projections, states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.errors import invalid_state, upload_expired
from app.modules.portfolio.lease import Lease, build, reject_rows
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
from app.modules.portfolio.repository import (
    current_upload,
    own_item,
    owning_profile_id,
    transaction,
)
from app.modules.portfolio.responses import ItemOwner
from app.shared.errors import AppError


def check_state(
    item: PortfolioItem, upload: PortfolioUpload | None, upload_id: UUID, now: datetime
) -> PortfolioUpload:
    if item.state == states.VALIDATING:
        # A live lease means a concurrent validation; an expired one is recoverable.
        if upload is None or upload.lease_until is None or upload.lease_until > now:
            raise invalid_state()
    elif item.state != states.PENDING:
        raise invalid_state()
    if upload is None or upload.id != upload_id:
        raise invalid_state()
    return upload


def acquire(
    context: PortfolioContext, user_id: UUID, item_id: UUID, upload_id: UUID, now: datetime
) -> Lease | ItemOwner:
    """Takes the item lock, moves to validating and releases the transaction before any I/O."""
    expiry: AppError | None = None
    lease: Lease | None = None
    with transaction(context.factory) as db:
        item = own_item(db, owning_profile_id(db, user_id), item_id, write=True)
        upload = current_upload(db, item.id, write=True)
        if item.state in states.FINAL_FILE:
            if upload is None or upload.id != upload_id:
                raise invalid_state()
            return projections.owner(item)
        current = check_state(item, upload, upload_id, now)
        if current.expires_at <= now:
            reject_rows(item, current, "UPLOAD_EXPIRED", now)
            expiry = upload_expired()
        else:
            current.lease_until = now + timedelta(seconds=states.LEASE_SECONDS)
            item.state = states.VALIDATING
            item.updated_at = now
            lease = build(user_id, item, current)
        db.flush()
    if expiry is not None:
        raise expiry
    assert lease is not None
    return lease
