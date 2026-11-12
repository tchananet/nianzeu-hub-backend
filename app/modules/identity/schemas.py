from datetime import datetime
from typing import Literal
from uuid import UUID

from email_validator import validate_email
from pydantic import Field, field_validator

from app.shared.dto import DTO


class EmailInput(DTO):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        result = validate_email(value, check_deliverability=False, allow_smtputf8=False)
        if result.ascii_email is None:
            raise ValueError("ASCII email required")
        normalized = result.ascii_email.lower()
        if len(normalized) > 254:
            raise ValueError("Email too long")
        return normalized


class PasswordInput(DTO):
    password: str = Field(min_length=12, max_length=128, repr=False)

    @field_validator("password")
    @classmethod
    def bound_password(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 512:
            raise ValueError("Password too long")
        return value


class CredentialsInput(EmailInput, PasswordInput):
    """Shared strict register/login input; role cannot be supplied."""


class ResetInput(PasswordInput):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43,128}$", repr=False)


class UserDTO(DTO):
    id: UUID
    email: str
    role: Literal["talent"] = "talent"
    created_at: datetime


class UserResponse(DTO):
    user: UserDTO


class LoginResponse(UserResponse):
    csrf_token: str = Field(repr=False)


class CsrfResponse(DTO):
    csrf_token: str = Field(repr=False)
