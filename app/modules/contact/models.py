from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.core.database import Base


class Contact(Base):
    __tablename__ = "contact_settings"
    __table_args__ = tuple(
        constraint for name in ("email", "phone", "whatsapp") for constraint in (
            CheckConstraint(f"{name} IS NULL OR length({name}) > 0",
                            name=conv(f"contact_settings_{name}_check")),
            CheckConstraint(f"NOT {name}_visible OR {name} IS NOT NULL",
                            name=conv(f"ck_contact_{name}")),
        )
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("talent_profiles.id", ondelete="CASCADE"), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(16))
    whatsapp: Mapped[str | None] = mapped_column(String(16))
    email_visible: Mapped[bool] = mapped_column(server_default="false")
    phone_visible: Mapped[bool] = mapped_column(server_default="false")
    whatsapp_visible: Mapped[bool] = mapped_column(server_default="false")
