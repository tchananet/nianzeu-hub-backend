import logging
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from starlette.responses import StreamingResponse

from app.modules.portfolio.concurrency import Slots
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.disposition import attachment
from app.modules.portfolio.repository import published_item, transaction
from app.shared.errors import DependencyUnavailable, StorageMissing

DOWNLOAD_CAPACITY = 20
logger = logging.getLogger("app.portfolio")


@dataclass(frozen=True)
class Delivery:
    key: str
    media_type: str
    size_bytes: int
    filename: str


def headers(delivery: Delivery) -> dict[str, str]:
    return {
        "Content-Length": str(delivery.size_bytes),
        "Content-Disposition": attachment(delivery.filename),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
        "Vary": "Origin",
    }


class ContentService:
    """Serves the private bucket through the API; no signed GET URL is ever issued."""

    def __init__(self, context: PortfolioContext, slots: Slots | None = None) -> None:
        self.context = context
        self.slots = slots or Slots(DOWNLOAD_CAPACITY, DependencyUnavailable)

    def lookup(self, item_id: UUID) -> Delivery:
        """Publication is re-checked in the database on every single read."""
        with transaction(self.context.factory) as db:
            item = published_item(db, item_id)
            if item.object_key is None or item.media_type is None:
                raise DependencyUnavailable()
            if item.size_bytes is None or item.filename is None:
                raise DependencyUnavailable()
            return Delivery(item.object_key, item.media_type, item.size_bytes, item.filename)

    def stream(self, item_id: UUID) -> StreamingResponse:
        delivery = self.lookup(item_id)
        self.slots.acquire()
        try:
            info = self.context.storage.head(self.context.validated_bucket, delivery.key)
            if info.size_bytes != delivery.size_bytes:
                logger.error("Published object size drift", extra={"code": "OBJECT_INVALID"})
                raise DependencyUnavailable()
        except StorageMissing:
            self.slots.release()
            logger.error("Published object absent", extra={"code": "OBJECT_MISSING"})
            raise DependencyUnavailable() from None
        except Exception:
            self.slots.release()
            raise
        return StreamingResponse(
            self.body(delivery.key), media_type=delivery.media_type, headers=headers(delivery)
        )

    def body(self, key: str) -> Iterator[bytes]:
        """Range is ignored at MVP: the full object is always returned with status 200."""
        try:
            with self.context.storage.read_stream(self.context.validated_bucket, key) as chunks:
                yield from chunks
        finally:
            self.slots.release()
