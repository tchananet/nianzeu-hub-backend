from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.profiles.constraints import certification_checks, experience_checks


class Experience(Base):
    __tablename__ = "experiences"
    __table_args__ = experience_checks()
    id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("talent_profiles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(150))
    organization: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(2000))
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    position: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = certification_checks()
    id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("talent_profiles.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(150))
    issuer: Mapped[str] = mapped_column(String(150))
    issued_on: Mapped[date]
    expires_on: Mapped[date | None]
    credential_url: Mapped[str | None] = mapped_column(String(2048))
    position: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
