from sqlalchemy.orm import Session, sessionmaker

from app.modules.discovery.filters import conditions
from app.modules.discovery.projection import summary
from app.modules.discovery.repository import count_matches, page_matches, skills_of
from app.modules.discovery.responses import ProfileSummary
from app.modules.discovery.schemas import SearchQuery
from app.modules.profiles.repository import transaction
from app.shared.dto import Page


class DiscoveryService:
    """Anonymous profile search: three bounded statements per call, whatever page_size is."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self.factory = factory

    def search(self, query: SearchQuery) -> Page[ProfileSummary]:
        clauses = conditions(query)
        with transaction(self.factory) as db:
            total = count_matches(db, clauses)
            rows = page_matches(db, clauses, query)
            skills = skills_of(db, [row.id for row in rows])
        return Page[ProfileSummary](
            items=[summary(row, skills.get(row.id, [])) for row in rows],
            page=query.page,
            page_size=query.page_size,
            total=total,
        )
