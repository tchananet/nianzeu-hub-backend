from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.portfolio.constraints import item_checks, upload_checks


class PortfolioItem(Base):
    __tablename__ = "portfolio_items"
    __table_args__ = item_checks()
    id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(2000))
    type: Mapped[str] = mapped_column(String(8))
    state: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    object_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    filename: Mapped[str | None] = mapped_column(String(120))
    media_type: Mapped[str | None] = mapped_column(String(80))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(CHAR(64))
    rejection_code: Mapped[str | None] = mapped_column(String(40))


class PortfolioUpload(Base):
    __tablename__ = "portfolio_uploads"
    __table_args__ = upload_checks()
    id: Mapped[UUID] = mapped_column(primary_key=True)
    item_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolio_items.id", ondelete="CASCADE"), unique=True
    )
    quarantine_key: Mapped[str] = mapped_column(String(255), unique=True)
    filename: Mapped[str] = mapped_column(String(120))
    media_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reservation_active: Mapped[bool] = mapped_column(Boolean)
