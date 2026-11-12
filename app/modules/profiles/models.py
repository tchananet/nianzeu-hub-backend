from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.core.database import Base
from app.modules.profiles.constraints import profile_checks


class Profile(Base):
    __tablename__ = "talent_profiles"
    __table_args__ = profile_checks()
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    headline: Mapped[str] = mapped_column(String(160))
    bio: Mapped[str] = mapped_column(String(5000))
    city: Mapped[str] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(CHAR(2))
    availability: Mapped[str] = mapped_column(String(16))
    experience_level: Mapped[str] = mapped_column(String(16))
    rate_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    rate_currency: Mapped[str | None] = mapped_column(CHAR(3))
    rate_unit: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint("length(name) > 0", name=conv("skills_name_check")),
        CheckConstraint("normalized_name = lower(name)", name=conv("ck_skills_normalized")),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True)


class ProfileSkill(Base):
    __tablename__ = "profile_skills"
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True)
