from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.contact.repository import read_contact
from app.modules.contact.schemas import public_contacts
from app.modules.profiles.children import Certification, Experience
from app.modules.profiles.entries import CertificationRead, ExperienceRead
from app.modules.profiles.models import Profile, ProfileSkill, Skill
from app.modules.profiles.responses import ProfileOwner, ProfilePublic, SkillRead
from app.modules.profiles.schemas import ProfileFields, Rate


def common(db: Session, row: Profile) -> tuple[dict[str, Any], list[SkillRead]]:
    fields = {name: getattr(row, name) for name in ProfileFields.model_fields if name != "rate"}
    fields.update(id=row.id, created_at=row.created_at, updated_at=row.updated_at)
    fields["rate"] = None if row.rate_amount is None else Rate.model_validate({
        "amount": format(row.rate_amount, ".2f"), "currency": row.rate_currency,
        "unit": row.rate_unit,
    })
    fields["experiences"] = [ExperienceRead.model_validate({
        name: getattr(item, name) for name in ExperienceRead.model_fields
    }) for item in db.scalars(select(Experience).where(Experience.profile_id == row.id)
                              .order_by(Experience.position))]
    fields["certifications"] = [CertificationRead.model_validate({
        name: getattr(item, name) for name in CertificationRead.model_fields
    }) for item in db.scalars(select(Certification).where(Certification.profile_id == row.id)
                              .order_by(Certification.position))]
    skills = [SkillRead(id=item.id, name=item.name) for item in db.scalars(
        select(Skill).join(ProfileSkill, ProfileSkill.skill_id == Skill.id)
        .where(ProfileSkill.profile_id == row.id).order_by(Skill.normalized_name, Skill.id))]
    return fields, skills


def owner(db: Session, row: Profile) -> ProfileOwner:
    fields, skills = common(db, row)
    return ProfileOwner(**fields, user_id=row.user_id, skill_ids=[s.id for s in skills],
                        contacts=read_contact(db, row.id))


def public(db: Session, row: Profile) -> ProfilePublic:
    fields, skills = common(db, row)
    return ProfilePublic(**fields, skills=skills,
                         contacts=public_contacts(read_contact(db, row.id)))
