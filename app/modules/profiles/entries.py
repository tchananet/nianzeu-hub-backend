from datetime import UTC, date, datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BeforeValidator, Field, field_validator, model_validator

from app.modules.profiles.validation import calendar_date, https_link
from app.shared.dto import DTO

CalendarDate = Annotated[date, BeforeValidator(calendar_date)]


class ExperienceWrite(DTO):
    title: str = Field(min_length=1, max_length=150)
    organization: str = Field(min_length=1, max_length=150)
    start_date: CalendarDate
    end_date: CalendarDate | None
    description: str = Field(max_length=2000)

    @model_validator(mode="after")
    def dates(self) -> Self:
        today = datetime.now(UTC).date()
        if self.start_date > today or self.end_date is not None and (
            self.end_date < self.start_date or self.end_date > today
        ):
            raise ValueError("Invalid experience dates")
        return self


class CertificationWrite(DTO):
    name: str = Field(min_length=1, max_length=150)
    issuer: str = Field(min_length=1, max_length=150)
    issued_on: CalendarDate
    expires_on: CalendarDate | None
    credential_url: str | None = Field(max_length=2048)

    @field_validator("credential_url")
    @classmethod
    def link(cls, value: str | None) -> str | None:
        return https_link(value) if value is not None else None

    @model_validator(mode="after")
    def dates(self) -> Self:
        if self.issued_on > datetime.now(UTC).date() or (
            self.expires_on is not None and self.expires_on < self.issued_on
        ):
            raise ValueError("Invalid certification dates")
        return self


class ExperienceRead(ExperienceWrite):
    id: UUID


class CertificationRead(CertificationWrite):
    id: UUID
