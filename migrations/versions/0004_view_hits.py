"""Count repeat profile views per visitor per day; no application imports."""

import os

from alembic import op
from sqlalchemy import text

revision = "0004_view_hits"
down_revision = "0003_portfolio_search"
branch_labels = None
depends_on = None

# One view per visitor per day made a popular profile look frozen. The per-visitor
# daily ceiling keeps a single address from inflating a count without bound.
VIEWS_PER_VISITOR_DAY = 100


def upgrade():
    op.execute(
        "ALTER TABLE profile_view_dedup ADD COLUMN hits smallint NOT NULL DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE profile_view_dedup ADD CONSTRAINT ck_profile_view_dedup_hits "
        f"CHECK (hits BETWEEN 1 AND {VIEWS_PER_VISITOR_DAY})"
    )


def downgrade():
    connection = op.get_bind()
    database = connection.execute(text("SELECT current_database()")).scalar_one()
    if (
        os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE") != "1"
        or connection.engine.url.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.endswith("_test")
    ):
        raise RuntimeError("Downgrade requires explicit opt-in and loopback _test database")
    op.execute("ALTER TABLE profile_view_dedup DROP CONSTRAINT ck_profile_view_dedup_hits")
    op.execute("ALTER TABLE profile_view_dedup DROP COLUMN hits")
