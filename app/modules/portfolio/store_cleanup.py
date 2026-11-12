import logging
from collections.abc import Iterable

from app.shared.errors import StorageInvalid, StorageMissing, StorageUnavailable
from app.shared.ports import StoragePort

logger = logging.getLogger("app.portfolio")


def drop_objects(storage: StoragePort, bucket: str, keys: Iterable[str]) -> int:
    """Best-effort physical deletion; failures are logged and retried by the cleanup command."""
    removed = 0
    for key in keys:
        try:
            storage.delete(bucket, key)
        except StorageMissing:
            removed += 1
        except (StorageUnavailable, StorageInvalid):
            logger.error("Object deletion deferred to cleanup", extra={"bucket": bucket})
        else:
            removed += 1
    return removed
