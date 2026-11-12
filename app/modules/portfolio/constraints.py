from sqlalchemy import CheckConstraint, Index
from sqlalchemy.schema import conv

STATES = "('draft', 'pending', 'validating', 'rejected', 'validated', 'published')"
FINAL_METADATA = (
    "object_key IS NOT NULL AND filename IS NOT NULL AND media_type IS NOT NULL"
    " AND size_bytes IS NOT NULL AND sha256 IS NOT NULL AND validated_at IS NOT NULL"
)
NO_METADATA = (
    "object_key IS NULL AND filename IS NULL AND media_type IS NULL"
    " AND size_bytes IS NULL AND sha256 IS NULL AND validated_at IS NULL"
)
HEX_64 = "~ '^[0-9a-f]{64}$'"


def non_empty(table: str, column: str, nullable: bool) -> CheckConstraint:
    """Reproduces an inline column CHECK, which PostgreSQL names <table>_<column>_check."""
    guard = f"{column} IS NULL OR " if nullable else ""
    return CheckConstraint(
        f"{guard}length({column}) > 0", name=conv(f"{table}_{column}_check")
    )


def item_checks() -> tuple[CheckConstraint | Index, ...]:
    """Mirrors migrations/versions/0003_portfolio_search_items.sql exactly (M03)."""
    return (
        CheckConstraint("type IN ('image', 'pdf', 'video')", name=conv("ck_portfolio_items_type")),
        CheckConstraint(f"state IN {STATES}", name=conv("ck_portfolio_items_state")),
        non_empty("portfolio_items", "title", nullable=False),
        non_empty("portfolio_items", "object_key", nullable=True),
        non_empty("portfolio_items", "filename", nullable=True),
        non_empty("portfolio_items", "media_type", nullable=True),
        non_empty("portfolio_items", "rejection_code", nullable=True),
        CheckConstraint(
            "size_bytes IS NULL OR (size_bytes >= 1 AND size_bytes <= 104857600)",
            name=conv("ck_portfolio_items_size"),
        ),
        CheckConstraint(
            f"sha256 IS NULL OR sha256 {HEX_64}", name=conv("ck_portfolio_items_sha256")
        ),
        CheckConstraint(
            f"CASE WHEN state IN ('validated', 'published') THEN {FINAL_METADATA}"
            f" ELSE {NO_METADATA} END",
            name=conv("ck_portfolio_items_final_metadata"),
        ),
        CheckConstraint(
            "(state = 'published') = (published_at IS NOT NULL)",
            name=conv("ck_portfolio_items_published_at"),
        ),
        Index(
            "ix_portfolio_items_profile_state_published",
            "profile_id", "state", "published_at", "id",
        ),
    )


def upload_checks() -> tuple[CheckConstraint, ...]:
    """Mirrors migrations/versions/0003_portfolio_search_uploads.sql exactly (M03)."""
    return (
        non_empty("portfolio_uploads", "quarantine_key", nullable=False),
        non_empty("portfolio_uploads", "filename", nullable=False),
        non_empty("portfolio_uploads", "media_type", nullable=False),
        CheckConstraint(
            "size_bytes > 0 AND size_bytes <= 104857600",
            name=conv("ck_portfolio_uploads_size"),
        ),
        CheckConstraint(f"sha256 {HEX_64}", name=conv("ck_portfolio_uploads_sha256")),
        CheckConstraint("expires_at > created_at", name=conv("ck_portfolio_uploads_expiry")),
    )
