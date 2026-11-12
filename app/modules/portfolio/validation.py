from collections.abc import Callable
from uuid import UUID

from app.modules.portfolio import inspection, lease_acquire, lease_writes, validation_io
from app.modules.portfolio.concurrency import Slots
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.download import sha256_hex
from app.modules.portfolio.errors import (
    Rejected,
    invalid_state,
    rejected_invalid,
    validation_busy,
)
from app.modules.portfolio.lease import Lease
from app.modules.portfolio.responses import ItemOwner
from app.modules.portfolio.schemas import ValidateRequest
from app.shared.errors import (
    DependencyUnavailable,
    StorageInvalid,
    StorageMissing,
    StorageUnavailable,
)

VALIDATION_CAPACITY = 2


class ValidationService:
    def __init__(
        self,
        context: PortfolioContext,
        slots: Slots | None = None,
        deadline: Callable[[], Deadline] = Deadline,
    ) -> None:
        self.context = context
        self.slots = slots or Slots(VALIDATION_CAPACITY, validation_busy)
        self.deadline = deadline

    def validate(self, user_id: UUID, item_id: UUID, data: ValidateRequest) -> ItemOwner:
        """Saturation is refused before any state change; the lease is taken afterwards."""
        self.slots.acquire()
        try:
            outcome = lease_acquire.acquire(
                self.context, user_id, item_id, data.upload_id, self.context.clock()
            )
            return outcome if isinstance(outcome, ItemOwner) else self.run(outcome)
        finally:
            self.slots.release()

    def run(self, lease: Lease) -> ItemOwner:
        deadline = self.deadline()
        try:
            content, etag = validation_io.fetch(self.context, lease, deadline)
            inspection.verify_declaration(
                lease.item_type, lease.media_type, lease.filename, lease.size_bytes
            )
            if sha256_hex(content) != lease.sha256:
                raise rejected_invalid("SHA256_MISMATCH")
            inspection.inspect(lease.item_type, lease.media_type, content, deadline)
            del content
            key, digest = validation_io.store(self.context, lease, etag, deadline)
            return lease_writes.finalize(self.context, lease, key, digest)
        except Rejected as rejection:
            lease_writes.reject(self.context, lease, rejection.rejection_code)
            raise rejection.error from None
        except StorageMissing:
            lease_writes.release(self.context, lease)
            raise invalid_state() from None
        except (StorageInvalid, StorageUnavailable):
            lease_writes.release(self.context, lease)
            raise DependencyUnavailable() from None
