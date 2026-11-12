from typing import cast

from app.modules.portfolio import states
from app.modules.portfolio.models import PortfolioItem
from app.modules.portfolio.responses import FileInfo, ItemOwner, ItemPublic
from app.modules.portfolio.schemas import ItemType


def content_url(item: PortfolioItem) -> str:
    return f"/api/v1/portfolio/{item.id}/content"


def file_info(item: PortfolioItem) -> FileInfo | None:
    if item.state not in states.FINAL_FILE:
        return None
    if item.filename is None or item.media_type is None:
        raise ValueError("Validated item without final metadata")
    if item.size_bytes is None or item.sha256 is None:
        raise ValueError("Validated item without final metadata")
    return FileInfo(
        filename=item.filename,
        media_type=item.media_type,
        size_bytes=item.size_bytes,
        sha256=item.sha256,
    )


def owner(item: PortfolioItem) -> ItemOwner:
    return ItemOwner(
        id=item.id,
        profile_id=item.profile_id,
        title=item.title,
        description=item.description,
        type=cast(ItemType, item.type),
        state=item.state,
        created_at=item.created_at,
        updated_at=item.updated_at,
        validated_at=item.validated_at,
        published_at=item.published_at,
        file=file_info(item),
        rejection_code=item.rejection_code,
    )


def public(item: PortfolioItem) -> ItemPublic:
    info = file_info(item)
    if item.state != states.PUBLISHED or info is None or item.published_at is None:
        raise ValueError("Public projection requires a published item")
    return ItemPublic(
        id=item.id,
        profile_id=item.profile_id,
        title=item.title,
        description=item.description,
        type=cast(ItemType, item.type),
        published_at=item.published_at,
        file=info,
        content_url=content_url(item),
    )
