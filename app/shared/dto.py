import unicodedata
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class DTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)

    @field_validator("*", mode="before")
    @classmethod
    def clean_strings(cls, value: object, info: ValidationInfo) -> object:
        if info.field_name == "password":
            return value
        if isinstance(value, str):
            if any(unicodedata.category(char) == "Cc" for char in value):
                raise ValueError("Control characters forbidden")
            return value.strip()
        return value


class Pagination(DTO):
    page: int = Field(default=1, ge=1, le=500)
    page_size: int = Field(default=20, ge=1, le=50)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @model_validator(mode="after")
    def bound_offset(self) -> Self:
        if self.offset > 10000:
            raise ValueError("Offset exceeds 10000")
        return self


class Page[T](DTO):
    items: list[T]
    page: int
    page_size: int
    total: int = Field(ge=0)
