from datetime import date
from uuid import UUID, uuid4

from tests.migrations.identity.helpers import NOW, insert, user

SKILL_ID = UUID("00000000-0000-4000-8000-000000000001")


def profile(connection, **changes):
    owner = changes.pop("user_id", None)
    if owner is None:
        owner = user(connection)
    values = dict(
        id=uuid4(), user_id=owner, display_name="Talent", headline="Engineer", bio="",
        city="Douala", country_code="CM", availability="immediate", experience_level="senior",
        created_at=NOW, updated_at=NOW,
    )
    values.update(changes)
    insert(connection, "talent_profiles", **values)
    return values["id"]


def entry(connection, table, profile_id, **changes):
    values = dict(id=uuid4(), profile_id=profile_id, position=0, created_at=NOW)
    if table == "experiences":
        values.update(title="Engineer", organization="Example", description="",
                      start_date=date(2025, 1, 1))
    else:
        values.update(name="Certificate", issuer="Example", issued_on=date(2025, 1, 1))
    values.update(changes)
    insert(connection, table, **values)
