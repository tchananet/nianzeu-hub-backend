from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.core.database import Base


class ProfileView(Base):
    __tablename__ = "profile_views"
    __table_args__ = (CheckConstraint("count >= 0", name=conv("profile_views_count_check")),)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    count: Mapped[int]


class ViewDedup(Base):
    __tablename__ = "profile_view_dedup"
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(primary_key=True)
    visitor_hash: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
