from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.config_urls import endpoint
from app.core.origins import normalize_origin, usable_origin


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="forbid", hide_input_in_errors=True)
    environment: Literal["local", "test", "production"]
    database_url: SecretStr
    storage_endpoint: str
    storage_public_endpoint: str
    storage_access_key: SecretStr = Field(min_length=1)
    storage_secret_key: SecretStr = Field(min_length=1)
    quarantine_bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
    validated_bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
    # Absent is legal outside production and means "enforce no origin at all": the
    # open mode used to reach the API directly over plain HTTP with no proxy.
    frontend_origin: str | None = None
    quota_hmac_secret: SecretStr = Field(min_length=32)
    secure_cookies: bool = True
    session_cross_site_enabled: bool = False
    docs_enabled: bool = False
    api_public_origin: str | None = None
    workers: int = Field(default=2, ge=1, le=20)
    pool_size: int = Field(default=5, ge=1, le=20)
    max_overflow: int = Field(default=5, ge=0, le=20)
    pool_timeout: int = Field(default=3, ge=1, le=3)
    statement_timeout_ms: int = Field(default=3000, ge=1, le=3000)

    @field_validator("frontend_origin", "api_public_origin", mode="before")
    @classmethod
    def blank_is_absent(cls, value: object) -> object:
        # Compose passes an unset variable through as "", which must not read as a value.
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("session_cross_site_enabled", "secure_cookies", "docs_enabled",
                     mode="before")
    @classmethod
    def strict_boolean(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ValueError("Expected boolean true or false")

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        try:
            url = make_url(self.database_url.get_secret_value())
            valid = (
                url.drivername == "postgresql+psycopg"
                and url.host
                and url.database
                and url.username
                and url.password
                and not url.query
            )
            if url.port is not None and not 1 <= url.port <= 65535:
                valid = False
        except Exception:
            raise ValueError("Invalid PostgreSQL URL") from None
        if not valid:
            raise ValueError("PostgreSQL psycopg URL with credentials required; no query options")
        local = self.environment in ("local", "test")
        if self.frontend_origin is not None:
            self.frontend_origin = usable_origin(self.frontend_origin, self.environment)
        elif not local:
            raise ValueError("A frontend origin is required in production")
        if self.api_public_origin is not None:
            self.api_public_origin = normalize_origin(self.api_public_origin)
        if self.session_cross_site_enabled and (
            not self.secure_cookies or self.api_public_origin is None
            or not self.api_public_origin.startswith("https://")
        ):
            raise ValueError("Cross-site sessions require HTTPS public origin and Secure cookies")
        if not self.secure_cookies and not local:
            raise ValueError("Insecure cookies require a non-production environment")
        self.storage_endpoint = endpoint(self.storage_endpoint, internal=True)
        self.storage_public_endpoint = endpoint(
            self.storage_public_endpoint, local_http=local, plain_http=local
        )
        if not local and not self.secure_cookies:
            raise ValueError("Secure cookies required outside local/test")
        if self.quarantine_bucket == self.validated_bucket:
            raise ValueError("Separate private buckets required")
        if self.workers * (self.pool_size + self.max_overflow) > 20:
            raise ValueError("API connection budget exceeds 20")
        return self
