from datetime import timedelta
from uuid import UUID, uuid4

from app.modules.portfolio import states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.errors import file_too_large, invalid_state, unsupported_media
from app.modules.portfolio.keys import quarantine_key
from app.modules.portfolio.limits import media_allowed, size_allowed
from app.modules.portfolio.models import PortfolioUpload
from app.modules.portfolio.quota import require_bytes
from app.modules.portfolio.repository import (
    current_upload,
    own_item,
    required_profile_id,
    transaction,
)
from app.modules.portfolio.responses import UploadTicket
from app.modules.portfolio.schemas import UploadRequest
from app.modules.portfolio.store_cleanup import drop_objects


class UploadService:
    """Reserves bytes and issues a presigned POST bound to one quarantine key."""

    def __init__(self, context: PortfolioContext) -> None:
        self.context = context

    def issue(self, user_id: UUID, data: UploadRequest) -> UploadTicket:
        now = self.context.clock()
        orphan: str | None = None
        with transaction(self.context.factory) as db:
            profile_id = required_profile_id(db, user_id, lock=True)
            item = own_item(db, profile_id, data.item_id, write=True)
            if item.state not in states.UPLOADABLE:
                raise invalid_state()
            if not media_allowed(item.type, data.media_type, data.filename):
                raise unsupported_media()
            if not size_allowed(item.type, data.size_bytes):
                raise file_too_large()
            previous = current_upload(db, item.id, write=True)
            if previous is not None:
                orphan = previous.quarantine_key
                db.delete(previous)
                db.flush()
            require_bytes(db, profile_id, data.size_bytes)
            upload = PortfolioUpload(
                id=uuid4(),
                item_id=item.id,
                quarantine_key=quarantine_key(),
                filename=data.filename,
                media_type=data.media_type,
                size_bytes=data.size_bytes,
                sha256=data.sha256,
                created_at=now,
                expires_at=now + timedelta(seconds=states.UPLOAD_TTL_SECONDS),
                lease_until=None,
                reservation_active=True,
            )
            db.add(upload)
            item.state = states.PENDING
            item.rejection_code = None
            item.updated_at = now
            db.flush()
            # Signing is local; failing here rolls the reservation back with no state change.
            ticket = self.presign(upload)
        if orphan is not None:
            drop_objects(self.context.storage, self.context.quarantine_bucket, [orphan])
        return ticket

    def presign(self, upload: PortfolioUpload) -> UploadTicket:
        signed = self.context.storage.presign_post(
            self.context.quarantine_bucket,
            upload.quarantine_key,
            upload.media_type,
            upload.size_bytes,
            upload.expires_at,
        )
        return UploadTicket(
            upload_id=upload.id,
            method="POST",
            url=signed.url,
            fields=signed.fields,
            expires_at=signed.expires_at,
        )
