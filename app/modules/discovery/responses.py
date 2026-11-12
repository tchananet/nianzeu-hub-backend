from typing import Literal
from uuid import UUID

from app.modules.profiles.responses import SkillRead
from app.modules.profiles.schemas import Rate
from app.shared.dto import DTO


class ProfileSummary(DTO):
    """Search projection of profiles.md: no bio, children, contacts, user_id or private flag.

    Deliberately not derived from ProfileFields: that model carries ``bio``, which the
    contract excludes from summaries. Enum literals mirror profiles.schemas.ProfileFields.
    """

    id: UUID
    display_name: str
    headline: str
    city: str
    country_code: str
    availability: Literal["immediate", "1-week", "freelance", "full-time"]
    experience_level: Literal["junior", "intermediate", "senior"]
    rate: Rate | None
    skills: list[SkillRead]
