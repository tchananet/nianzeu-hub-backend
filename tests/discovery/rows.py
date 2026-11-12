from decimal import Decimal
from uuid import uuid4

from app.core.primitives import utc_now
from app.modules.profiles.models import Profile

PUBLIC_FIELDS = {
    "id", "display_name", "headline", "city", "country_code",
    "availability", "experience_level", "rate", "skills",
}
PRIVATE_MARKERS = (
    "secret-bio", "login@example.com", "+237600000001", "+237600000002",
    "user_id", "email", "phone", "whatsapp", "contacts", "bio",
    "experiences", "certifications", "created_at", "updated_at", "skill_ids",
)


def profile_row(**overrides):
    """Detached ORM row carrying a private bio and a private owner link."""
    values = dict(
        id=uuid4(), user_id=uuid4(), display_name="Ada", headline="Developer",
        bio="secret-bio", city="Douala", country_code="CM", availability="freelance",
        experience_level="senior", rate_amount=Decimal("15000.00"), rate_currency="XAF",
        rate_unit="hour", created_at=utc_now(), updated_at=utc_now(),
    )
    values.update(overrides)
    return Profile(**values)
