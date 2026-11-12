from datetime import datetime
from uuid import UUID

from app.modules.contact.schemas import ContactPublic, ContactWrite
from app.modules.profiles.entries import CertificationRead, ExperienceRead
from app.modules.profiles.schemas import ProfileFields
from app.shared.dto import DTO


class SkillRead(DTO):
    id: UUID
    name: str


class ProfileRead(ProfileFields):
    id: UUID
    created_at: datetime
    updated_at: datetime
    experiences: list[ExperienceRead]
    certifications: list[CertificationRead]


class ProfileOwner(ProfileRead):
    user_id: UUID
    skill_ids: list[UUID]
    contacts: ContactWrite


class ProfilePublic(ProfileRead):
    skills: list[SkillRead]
    contacts: ContactPublic
