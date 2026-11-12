from typing import Annotated, Literal, Self
from uuid import UUID

import pycountry
from pydantic import BeforeValidator, Field, field_validator, model_validator

from app.modules.profiles.validation import uuid_value
from app.shared.dto import Pagination

SkillId = Annotated[UUID, BeforeValidator(uuid_value)]


class SearchQuery(Pagination):
    """Filters of profiles.md GET /search/profiles; same constraints as the profile fields."""

    q: str | None = Field(default=None, min_length=1, max_length=100)
    skill_ids: list[SkillId] = Field(default_factory=list, alias="skill_id", max_length=10)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    availability: Literal["immediate", "1-week", "freelance", "full-time"] | None = None
    experience_level: Literal["junior", "intermediate", "senior"] | None = None

    @field_validator("country_code")
    @classmethod
    def country(cls, value: str | None) -> str | None:
        if value is not None and pycountry.countries.get(alpha_2=value) is None:
            raise ValueError("Unknown country code")
        return value

    @model_validator(mode="after")
    def distinct_skills(self) -> Self:
        if len(self.skill_ids) != len(set(self.skill_ids)):
            raise ValueError("Repeated skill_id")
        return self
