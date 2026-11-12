from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.core.config_urls import endpoint


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
    frontend_origin: str
    quota_hmac_secret: SecretStr = Field(min_length=32)
    secure_cookies: bool = True
    workers: int = Field(default=2, ge=1, le=20)
    pool_size: int = Field(default=5, ge=1, le=20)
    max_overflow: int = Field(default=5, ge=0, le=20)
    pool_timeout: int = Field(default=3, ge=1, le=3)
    statement_timeout_ms: int = Field(default=3000, ge=1, le=3000)

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
        self.frontend_origin = endpoint(self.frontend_origin, local_http=local)
        self.storage_endpoint = endpoint(self.storage_endpoint, internal=True)
        self.storage_public_endpoint = endpoint(self.storage_public_endpoint, local_http=local)
        if not local and not self.secure_cookies:
            raise ValueError("Secure cookies required outside local/test")
        if self.quarantine_bucket == self.validated_bucket:
            raise ValueError("Separate private buckets required")
        if self.workers * (self.pool_size + self.max_overflow) > 20:
            raise ValueError("API connection budget exceeds 20")
        return self
