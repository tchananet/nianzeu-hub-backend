from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.exceptions import RequestValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.contact.repository import write_contact
from app.modules.profiles.children import Certification, Experience
from app.modules.profiles.models import Profile, ProfileSkill, Skill
from app.modules.profiles.repository import lock_user
from app.modules.profiles.schemas import ProfileWrite


def replace(db: Session, user_id: UUID, data: ProfileWrite, now: datetime) -> tuple[Profile, bool]:
    lock_user(db, user_id)
    row = db.scalar(select(Profile).where(Profile.user_id == user_id).with_for_update())
    known = set(db.scalars(select(Skill.id).where(Skill.id.in_(data.skill_ids))))
    if known != set(data.skill_ids):
        raise RequestValidationError([{"loc": ("body", "skill_ids"), "type": "value_error"}])
    created = row is None
    if row is None:
        row = Profile(id=uuid4(), user_id=user_id, created_at=now)
        db.add(row)
    for name, value in data.model_dump(exclude={
        "rate", "skill_ids", "experiences", "certifications", "contacts",
    }).items():
        setattr(row, name, value)
    row.updated_at = now
    row.rate_amount = Decimal(data.rate.amount) if data.rate else None
    row.rate_currency = data.rate.currency if data.rate else None
    row.rate_unit = data.rate.unit if data.rate else None
    db.flush()
    for model in (Experience, Certification, ProfileSkill):
        db.execute(delete(model).where(model.profile_id == row.id))
    db.add_all([ProfileSkill(profile_id=row.id, skill_id=skill_id) for skill_id in data.skill_ids])
    db.add_all([Experience(id=uuid4(), profile_id=row.id, position=i, created_at=now,
                          **item.model_dump()) for i, item in enumerate(data.experiences)])
    db.add_all([Certification(id=uuid4(), profile_id=row.id, position=i, created_at=now,
                             **item.model_dump()) for i, item in enumerate(data.certifications)])
    write_contact(db, row.id, data.contacts)
    db.flush()
    return row, created
