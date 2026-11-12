from uuid import UUID

from sqlalchemy import ColumnElement, Select, distinct, func, or_, select

from app.modules.discovery.schemas import SearchQuery
from app.modules.profiles.models import Profile, ProfileSkill

ESCAPE = "\\"


def literal_pattern(value: str) -> str:
    """Treat %, _ and the escape character itself as literals; never as wildcards."""
    escaped = value.replace(ESCAPE, ESCAPE * 2)
    escaped = escaped.replace("%", f"{ESCAPE}%").replace("_", f"{ESCAPE}_")
    return f"%{escaped.lower()}%"


def keyword_clause(value: str) -> ColumnElement[bool]:
    pattern = literal_pattern(value)
    return or_(
        func.lower(Profile.display_name).like(pattern, escape=ESCAPE),
        func.lower(Profile.headline).like(pattern, escape=ESCAPE),
        func.lower(Profile.bio).like(pattern, escape=ESCAPE),
    )


def skill_subquery(skill_ids: list[UUID]) -> Select[tuple[UUID]]:
    """AND semantics: a profile must carry every requested skill."""
    return (
        select(ProfileSkill.profile_id)
        .where(ProfileSkill.skill_id.in_(skill_ids))
        .group_by(ProfileSkill.profile_id)
        .having(func.count(distinct(ProfileSkill.skill_id)) == len(skill_ids))
    )


def conditions(query: SearchQuery) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if query.q is not None:
        clauses.append(keyword_clause(query.q))
    if query.city is not None:
        clauses.append(func.lower(Profile.city) == query.city.lower())
    if query.country_code is not None:
        clauses.append(Profile.country_code == query.country_code)
    if query.availability is not None:
        clauses.append(Profile.availability == query.availability)
    if query.experience_level is not None:
        clauses.append(Profile.experience_level == query.experience_level)
    if query.skill_ids:
        clauses.append(Profile.id.in_(skill_subquery(query.skill_ids)))
    return clauses
