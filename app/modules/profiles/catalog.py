from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.profiles.models import Skill
from app.modules.profiles.repository import transaction
from app.modules.profiles.responses import SkillRead
from app.shared.dto import Page, Pagination


class SkillsQuery(Pagination):
    q: str | None = Field(default=None, min_length=1, max_length=80)


def parse_query(request: Request) -> SkillsQuery:
    values: dict[str, object] = {}
    for name in request.query_params:
        entries = request.query_params.getlist(name)
        if name not in {"page", "page_size", "q"} or len(entries) != 1:
            raise RequestValidationError([{"loc": ("query", name), "type": "value_error"}])
        value = entries[0]
        if name != "q":
            if not value.isascii() or not value.isdecimal() or len(value) > 5:
                raise RequestValidationError([{"loc": ("query", name), "type": "value_error"}])
            values[name] = int(value)
        else:
            values[name] = value
    try:
        return SkillsQuery.model_validate(values)
    except ValidationError as error:
        raise RequestValidationError([{"loc": ("query", *item["loc"]), "type": "value_error"}
                                      for item in error.errors(include_input=False)]) from None


def list_skills(factory: sessionmaker[Session], query: SkillsQuery) -> Page[SkillRead]:
    statement = select(Skill)
    if query.q is not None:
        literal = query.q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(Skill.normalized_name.like(f"%{literal}%", escape="\\"))
    with transaction(factory) as db:
        total = db.scalar(select(func.count()).select_from(statement.subquery()))
        rows = db.scalars(statement.order_by(Skill.normalized_name, Skill.id)
                          .offset(query.offset).limit(query.page_size))
        return Page[SkillRead](items=[SkillRead(id=s.id, name=s.name) for s in rows],
                               page=query.page, page_size=query.page_size, total=total or 0)
