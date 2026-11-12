from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.portfolio import states
from app.modules.portfolio.models import PortfolioItem, PortfolioUpload
from app.modules.portfolio.repository import current_upload


@dataclass(frozen=True)
class Lease:
    """Validation permit: item, upload and the exact lease instant that proves ownership."""

    user_id: UUID
    item_id: UUID
    upload_id: UUID
    item_type: str
    quarantine_key: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    lease_until: datetime


def build(user_id: UUID, item: PortfolioItem, upload: PortfolioUpload) -> Lease:
    if upload.lease_until is None:
        raise ValueError("Lease instant required")
    return Lease(
        user_id=user_id,
        item_id=item.id,
        upload_id=upload.id,
        item_type=item.type,
        quarantine_key=upload.quarantine_key,
        filename=upload.filename,
        media_type=upload.media_type,
        size_bytes=upload.size_bytes,
        sha256=upload.sha256,
        lease_until=upload.lease_until,
    )


def reject_rows(item: PortfolioItem, upload: PortfolioUpload, code: str, now: datetime) -> None:
    item.state = states.REJECTED
    item.rejection_code = code
    item.updated_at = now
    upload.reservation_active = False
    upload.lease_until = None


def held(item: PortfolioItem | None, upload: PortfolioUpload | None, lease: Lease) -> bool:
    return (
        item is not None
        and item.state == states.VALIDATING
        and upload is not None
        and upload.id == lease.upload_id
        and upload.lease_until == lease.lease_until
    )


def locked_rows(
    db: Session, item_id: UUID
) -> tuple[PortfolioItem | None, PortfolioUpload | None]:
    item = db.get(PortfolioItem, item_id, with_for_update=True)
    return item, None if item is None else current_upload(db, item_id, write=True)
