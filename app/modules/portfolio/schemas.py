from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, field_validator

from app.modules.portfolio.limits import MAX_BYTES, valid_filename
from app.modules.profiles.validation import uuid_value
from app.shared.dto import DTO

ItemType = Literal["image", "pdf", "video"]
# Strict DTOs refuse string coercion; JSON bodies carry UUIDs as text (same rule as P01).
Identifier = Annotated[UUID, BeforeValidator(uuid_value)]


class ItemCreate(DTO):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=2000)
    type: ItemType


class UploadRequest(DTO):
    item_id: Identifier
    filename: str = Field(min_length=1, max_length=120)
    media_type: str = Field(min_length=1, max_length=80)
    size_bytes: int = Field(ge=1, le=max(MAX_BYTES.values()))
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("filename")
    @classmethod
    def basename(cls, value: str) -> str:
        if not valid_filename(value):
            raise ValueError("Unsafe filename")
        return value


class ValidateRequest(DTO):
    upload_id: Identifier
