import logging
from uuid import UUID

from app.modules.portfolio import projections, states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.errors import invalid_state
from app.modules.portfolio.repository import own_item, owning_profile_id, transaction
from app.modules.portfolio.responses import ItemOwner
from app.shared.errors import DependencyUnavailable, StorageMissing

logger = logging.getLogger("app.portfolio")


class PublishingService:
    def __init__(self, context: PortfolioContext) -> None:
        self.context = context

    def publish(self, user_id: UUID, item_id: UUID) -> ItemOwner:
        """Publication requires a validated item whose final object is really present."""
        with transaction(self.context.factory) as db:
            item = own_item(db, owning_profile_id(db, user_id), item_id)
            if item.state == states.PUBLISHED:
                return projections.owner(item)
            if item.state != states.VALIDATED:
                raise invalid_state()
            key, size = item.object_key, item.size_bytes
        if key is None or size is None:
            raise DependencyUnavailable()
        self.require_object(key, size)
        return self.commit(user_id, item_id, key)

    def commit(self, user_id: UUID, item_id: UUID, key: str) -> ItemOwner:
        now = self.context.clock()
        with transaction(self.context.factory) as db:
            item = own_item(db, owning_profile_id(db, user_id), item_id, write=True)
            if item.state == states.PUBLISHED:
                return projections.owner(item)
            if item.state != states.VALIDATED or item.object_key != key:
                raise invalid_state()
            item.state = states.PUBLISHED
            item.published_at = now
            item.updated_at = now
            db.flush()
            return projections.owner(item)

    def require_object(self, key: str, size: int) -> None:
        try:
            info = self.context.storage.head(self.context.validated_bucket, key)
        except StorageMissing:
            logger.error("Validated object absent", extra={"code": "OBJECT_MISSING"})
            raise DependencyUnavailable() from None
        if info.size_bytes != size:
            logger.error("Validated object size drift", extra={"code": "OBJECT_INVALID"})
            raise DependencyUnavailable()

    def unpublish(self, user_id: UUID, item_id: UUID) -> ItemOwner:
        now = self.context.clock()
        with transaction(self.context.factory) as db:
            item = own_item(db, owning_profile_id(db, user_id), item_id, write=True)
            if item.state == states.VALIDATED:
                return projections.owner(item)
            if item.state != states.PUBLISHED:
                raise invalid_state()
            item.state = states.VALIDATED
            item.published_at = None
            item.updated_at = now
            db.flush()
            return projections.owner(item)
