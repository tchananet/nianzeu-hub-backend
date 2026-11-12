"""Portfolio items, uploads and search indexes; no application imports."""

import os
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "0003_portfolio_search"
down_revision = "0002_profiles"
branch_labels = None
depends_on = None

SEARCH_INDEXES = (
    ("talent_profiles", "ix_talent_profiles_updated_at_id"),
    ("talent_profiles", "ix_talent_profiles_availability"),
    ("talent_profiles", "ix_talent_profiles_experience_level"),
    ("talent_profiles", "ix_talent_profiles_country_city"),
    ("profile_skills", "ix_profile_skills_skill_profile"),
)


def upgrade():
    for section in ("items", "uploads", "indexes"):
        path = Path(__file__).with_name(f"0003_portfolio_search_{section}.sql")
        for statement in path.read_text(encoding="utf-8").split(";"):
            if statement.strip():
                op.execute(statement)


def downgrade():
    connection = op.get_bind()
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    if (
        os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE") != "1"
        or connection.engine.url.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.endswith("_test")
    ):
        raise RuntimeError("Downgrade requires explicit opt-in and loopback _test database")
    for table, index in SEARCH_INDEXES:
        op.drop_index(index, table_name=table)
    for table in ("portfolio_uploads", "portfolio_items"):
        op.drop_table(table)
