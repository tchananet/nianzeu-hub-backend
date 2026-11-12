from app.modules.discovery.responses import ProfileSummary
from app.modules.profiles.models import Profile
from app.modules.profiles.responses import SkillRead
from app.modules.profiles.schemas import Rate

FIELDS = ("display_name", "headline", "city", "country_code", "availability", "experience_level")


def rate_of(row: Profile) -> Rate | None:
    if row.rate_amount is None:
        return None
    return Rate.model_validate({
        "amount": format(row.rate_amount, ".2f"),
        "currency": row.rate_currency,
        "unit": row.rate_unit,
    })


def summary(row: Profile, skills: list[SkillRead]) -> ProfileSummary:
    """Only contract-listed public columns are read; bio and contacts are never touched."""
    return ProfileSummary.model_validate({
        "id": row.id,
        **{name: getattr(row, name) for name in FIELDS},
        "rate": rate_of(row),
        "skills": skills,
    })
