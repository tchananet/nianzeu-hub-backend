from datetime import timedelta
from uuid import uuid4

from tests.migrations.identity.helpers import NOW, insert

TABLES = {"portfolio_items", "portfolio_uploads"}
SEARCH_INDEXES = {
    "talent_profiles": {
        "ix_talent_profiles_updated_at_id", "ix_talent_profiles_availability",
        "ix_talent_profiles_experience_level", "ix_talent_profiles_country_city",
    },
    "profile_skills": {"ix_profile_skills_skill_profile"},
    "portfolio_items": {"ix_portfolio_items_profile_state_published"},
}


def final_metadata(**changes):
    values = dict(
        object_key=f"final/{uuid4().hex}", filename="demo.jpg", media_type="image/jpeg",
        size_bytes=1024, sha256="b" * 64, validated_at=NOW,
    )
    values.update(changes)
    return values


def item(connection, owner, **changes):
    values = dict(
        id=uuid4(), profile_id=owner, title="Demo", description="", type="image",
        state="draft", created_at=NOW, updated_at=NOW,
    )
    values.update(changes)
    insert(connection, "portfolio_items", **values)
    return values["id"]


def validated_item(connection, owner, **changes):
    values = final_metadata(state="validated")
    values.update(changes)
    return item(connection, owner, **values)


def upload(connection, owner_item, **changes):
    values = dict(
        id=uuid4(), item_id=owner_item, quarantine_key=f"quarantine/{uuid4().hex}",
        filename="demo.jpg", media_type="image/jpeg", size_bytes=1024, sha256="c" * 64,
        created_at=NOW, expires_at=NOW + timedelta(minutes=5), reservation_active=True,
    )
    values.update(changes)
    insert(connection, "portfolio_uploads", **values)
    return values["id"]
