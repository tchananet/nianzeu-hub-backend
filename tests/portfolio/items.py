from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.portfolio import projections
from app.modules.portfolio.models import PortfolioItem
from app.modules.portfolio.responses import ItemOwner, ItemPublic

NOW = datetime(2026, 11, 12, 10, 30, tzinfo=UTC)
DIGEST = "b" * 64


def item(profile_id: UUID | None = None, **overrides: object) -> PortfolioItem:
    fields: dict[str, object] = {
        "id": uuid4(),
        "profile_id": profile_id or uuid4(),
        "title": "Case study",
        "description": "Details",
        "type": "image",
        "state": "draft",
        "created_at": NOW,
        "updated_at": NOW,
    }
    return PortfolioItem(**(fields | overrides))


def validated(profile_id: UUID | None = None, **overrides: object) -> PortfolioItem:
    final: dict[str, object] = {
        "state": "validated",
        "validated_at": NOW,
        "object_key": f"items/{uuid4()}/{uuid4().hex}",
        "filename": "shot.png",
        "media_type": "image/png",
        "size_bytes": 1024,
        "sha256": DIGEST,
    }
    return item(profile_id, **(final | overrides))


def published(profile_id: UUID | None = None) -> PortfolioItem:
    return validated(profile_id, state="published", published_at=NOW)


def owner_dto() -> ItemOwner:
    return projections.owner(validated())


def public_dto() -> ItemPublic:
    return projections.public(published())
