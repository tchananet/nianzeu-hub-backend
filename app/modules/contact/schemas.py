from typing import Self

from pydantic import Field, field_validator, model_validator

from app.modules.identity.schemas import EmailInput
from app.shared.dto import DTO


class ContactPublic(DTO):
    email: str | None
    phone: str | None
    whatsapp: str | None


class ContactWrite(DTO):
    email: str | None = Field(max_length=254)
    phone: str | None = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    whatsapp: str | None = Field(pattern=r"^\+[1-9][0-9]{7,14}$")
    email_visible: bool
    phone_visible: bool
    whatsapp_visible: bool

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return EmailInput(email=value).email if value is not None else None

    @model_validator(mode="after")
    def visible_requires_value(self) -> Self:
        for field in ("email", "phone", "whatsapp"):
            if getattr(self, field + "_visible") and getattr(self, field) is None:
                raise ValueError("Visible contact requires a value")
        return self


def public_contacts(value: ContactWrite) -> ContactPublic:
    return ContactPublic(
        email=value.email if value.email_visible else None,
        phone=value.phone if value.phone_visible else None,
        whatsapp=value.whatsapp if value.whatsapp_visible else None,
    )
