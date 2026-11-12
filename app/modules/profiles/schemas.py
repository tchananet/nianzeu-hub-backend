from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

import pycountry
from pydantic import BeforeValidator, Field, field_validator

from app.modules.contact.schemas import ContactWrite
from app.modules.profiles.entries import CertificationWrite, ExperienceWrite
from app.modules.profiles.validation import uuid_value
from app.shared.dto import DTO


class Rate(DTO):
    amount: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,7})\.[0-9]{2}$")
    currency: Literal["XAF"]
    unit: Literal["hour", "day", "project"]

    @field_validator("amount")
    @classmethod
    def integral_xaf(cls, value: str) -> str:
        amount = Decimal(value)
        if amount <= 0 or amount != amount.to_integral_value():
            raise ValueError("Positive integral XAF amount required")
        return value


class ProfileFields(DTO):
    display_name: str = Field(min_length=1, max_length=100)
    headline: str = Field(min_length=1, max_length=160)
    bio: str = Field(max_length=5000)
    city: str = Field(min_length=1, max_length=100)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    availability: Literal["immediate", "1-week", "freelance", "full-time"]
    experience_level: Literal["junior", "intermediate", "senior"]
    rate: Rate | None

    @field_validator("country_code")
    @classmethod
    def country(cls, value: str) -> str:
        if pycountry.countries.get(alpha_2=value) is None:
            raise ValueError("Unknown country code")
        return value


class ProfileWrite(ProfileFields):
    skill_ids: list[Annotated[UUID, BeforeValidator(uuid_value)]] = Field(max_length=30)
    experiences: list[ExperienceWrite] = Field(max_length=20)
    certifications: list[CertificationWrite] = Field(max_length=20)
    contacts: ContactWrite

    @field_validator("skill_ids")
    @classmethod
    def unique_skills(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate skills")
        return value
