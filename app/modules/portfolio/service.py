from uuid import UUID, uuid4

from app.modules.portfolio import listing, projections, states
from app.modules.portfolio.context import PortfolioContext
from app.modules.portfolio.models import PortfolioItem
from app.modules.portfolio.quota import require_item_slot
from app.modules.portfolio.repository import (
    current_upload,
    existing_profile,
    own_item,
    owning_profile_id,
    profile_id_of,
    required_profile_id,
    transaction,
)
from app.modules.portfolio.responses import ItemOwner, ItemPublic
from app.modules.portfolio.schemas import ItemCreate
from app.modules.portfolio.store_cleanup import drop_objects
from app.shared.dto import Page, Pagination


class PortfolioService:
    def __init__(self, context: PortfolioContext) -> None:
        self.context = context

    def create(self, user_id: UUID, data: ItemCreate) -> ItemOwner:
        now = self.context.clock()
        with transaction(self.context.factory) as db:
            profile_id = required_profile_id(db, user_id, lock=True)
            require_item_slot(db, profile_id)
            item = PortfolioItem(
                id=uuid4(),
                profile_id=profile_id,
                title=data.title,
                description=data.description,
                type=data.type,
                state=states.DRAFT,
                created_at=now,
                updated_at=now,
            )
            db.add(item)
            db.flush()
            return projections.owner(item)

    def list_owner(self, user_id: UUID, query: Pagination) -> Page[ItemOwner]:
        with transaction(self.context.factory) as db:
            profile_id = profile_id_of(db, user_id)
            if profile_id is None:
                return Page[ItemOwner](
                    items=[], page=query.page, page_size=query.page_size, total=0
                )
            return listing.owner_page(db, profile_id, query)

    def get_owner(self, user_id: UUID, item_id: UUID) -> ItemOwner:
        with transaction(self.context.factory) as db:
            profile_id = owning_profile_id(db, user_id)
            return projections.owner(own_item(db, profile_id, item_id))

    def list_public(self, profile_id: UUID, query: Pagination) -> Page[ItemPublic]:
        with transaction(self.context.factory) as db:
            return listing.public_page(db, existing_profile(db, profile_id), query)

    def delete(self, user_id: UUID, item_id: UUID) -> None:
        """Database row first; orphaned objects are removed best effort then by cleanup."""
        with transaction(self.context.factory) as db:
            profile_id = owning_profile_id(db, user_id)
            item = own_item(db, profile_id, item_id, write=True)
            upload = current_upload(db, item.id, write=True)
            final_key = item.object_key
            quarantine_key = upload.quarantine_key if upload is not None else None
            db.delete(item)
        if quarantine_key is not None:
            drop_objects(self.context.storage, self.context.quarantine_bucket, [quarantine_key])
        if final_key is not None:
            drop_objects(self.context.storage, self.context.validated_bucket, [final_key])
