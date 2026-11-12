from collections import defaultdict
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.modules.profiles.models import Profile, ProfileSkill, Skill
from app.modules.profiles.responses import SkillRead
from app.shared.dto import Pagination


def count_matches(db: Session, clauses: list[ColumnElement[bool]]) -> int:
    statement = select(func.count()).select_from(Profile).where(*clauses)
    return db.scalar(statement) or 0


def page_matches(
    db: Session, clauses: list[ColumnElement[bool]], page: Pagination
) -> list[Profile]:
    """Stable sort of profiles.md: updated_at DESC then id ASC as last criterion."""
    statement = (
        select(Profile)
        .where(*clauses)
        .order_by(Profile.updated_at.desc(), Profile.id.asc())
        .offset(page.offset)
        .limit(page.page_size)
    )
    return list(db.scalars(statement))


def skills_of(db: Session, profile_ids: list[UUID]) -> dict[UUID, list[SkillRead]]:
    """One batched query for the whole page; never one query per profile."""
    grouped: dict[UUID, list[SkillRead]] = defaultdict(list)
    if not profile_ids:
        return grouped
    rows = db.execute(
        select(ProfileSkill.profile_id, Skill.id, Skill.name)
        .join(Skill, Skill.id == ProfileSkill.skill_id)
        .where(ProfileSkill.profile_id.in_(profile_ids))
        .order_by(ProfileSkill.profile_id, Skill.normalized_name, Skill.id)
    )
    for profile_id, skill_id, name in rows:
        grouped[profile_id].append(SkillRead(id=skill_id, name=name))
    return grouped
