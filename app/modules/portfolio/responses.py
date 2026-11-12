from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.portfolio.schemas import ItemType
from app.shared.dto import DTO


class FileInfo(DTO):
    filename: str
    media_type: str
    size_bytes: int
    sha256: str


class ItemOwner(DTO):
    id: UUID
    profile_id: UUID
    title: str
    description: str
    type: ItemType
    state: str
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None
    published_at: datetime | None
    file: FileInfo | None
    rejection_code: str | None


class ItemPublic(DTO):
    id: UUID
    profile_id: UUID
    title: str
    description: str
    type: ItemType
    published_at: datetime
    file: FileInfo
    content_url: str


class UploadTicket(DTO):
    upload_id: UUID
    method: Literal["POST"]
    url: str
    fields: dict[str, str]
    expires_at: datetime
