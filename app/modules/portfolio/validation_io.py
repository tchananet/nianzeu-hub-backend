from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.deadline import Deadline
from app.modules.portfolio.download import hash_stream, read_bounded
from app.modules.portfolio.errors import rejected_invalid, rejected_too_large
from app.modules.portfolio.keys import final_key
from app.modules.portfolio.lease import Lease
from app.modules.portfolio.limits import MAX_BYTES
from app.modules.portfolio.store_cleanup import drop_objects
from app.shared.errors import StorageInvalid


def fetch(context: PortfolioContext, lease: Lease, deadline: Deadline) -> tuple[bytes, str]:
    """Reads the quarantine object once, bounded by the announced size and the memory budget."""
    bucket = context.quarantine_bucket
    info = context.storage.head(bucket, lease.quarantine_key)
    if info.size_bytes > MAX_BYTES[lease.item_type]:
        raise rejected_too_large()
    if info.size_bytes != lease.size_bytes:
        raise rejected_invalid("SIZE_MISMATCH")
    with context.storage.read_stream(bucket, lease.quarantine_key) as chunks:
        content = read_bounded(chunks, deadline, lease.size_bytes)
    if len(content) != lease.size_bytes:
        raise rejected_invalid("SIZE_MISMATCH")
    return content, info.etag


def store(
    context: PortfolioContext, lease: Lease, etag: str, deadline: Deadline
) -> tuple[str, str]:
    """Conditional copy to a fresh key, then SHA recomputed on the final copy itself."""
    destination, key = context.validated_bucket, final_key(lease.item_id)
    context.storage.copy(
        context.quarantine_bucket, lease.quarantine_key, destination, key, etag
    )
    info = context.storage.head(destination, key)
    with context.storage.read_stream(destination, key) as chunks:
        digest, total = hash_stream(chunks, deadline, lease.size_bytes)
    if digest != lease.sha256 or total != lease.size_bytes or info.size_bytes != total:
        drop_objects(context.storage, destination, [key])
        raise StorageInvalid()
    return key, digest
