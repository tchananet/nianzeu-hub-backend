from sqlalchemy import CheckConstraint, Index
from sqlalchemy.schema import conv

STATES = "('draft','pending','validating','rejected','validated','published')"
FINAL_METADATA = (
    "object_key IS NOT NULL AND filename IS NOT NULL AND media_type IS NOT NULL"
    " AND size_bytes IS NOT NULL AND sha256 IS NOT NULL AND validated_at IS NOT NULL"
)
NO_METADATA = (
    "object_key IS NULL AND filename IS NULL AND media_type IS NULL"
    " AND size_bytes IS NULL AND sha256 IS NULL AND validated_at IS NULL"
)


def item_checks() -> tuple[CheckConstraint | Index, ...]:
    """Mirrors the portfolio_items DDL specified in docs/contracts/data.md (M03)."""
    return (
        CheckConstraint("type IN ('image','pdf','video')", name=conv("ck_portfolio_items_type")),
        CheckConstraint(f"state IN {STATES}", name=conv("ck_portfolio_items_state")),
        CheckConstraint("length(title) > 0", name=conv("portfolio_items_title_check")),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes BETWEEN 1 AND 104857600",
            name=conv("ck_portfolio_items_size"),
        ),
        CheckConstraint(
            "sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'",
            name=conv("ck_portfolio_items_sha256"),
        ),
        CheckConstraint(
            f"CASE WHEN state IN ('validated','published') THEN {FINAL_METADATA}"
            f" ELSE {NO_METADATA} END",
            name=conv("ck_portfolio_items_metadata"),
        ),
        CheckConstraint(
            "(state = 'published') = (published_at IS NOT NULL)",
            name=conv("ck_portfolio_items_published"),
        ),
        Index(
            "ix_portfolio_items_profile_id_state",
            "profile_id", "state", "published_at", "id",
        ),
    )


def upload_checks() -> tuple[CheckConstraint, ...]:
    """Mirrors the portfolio_uploads DDL specified in docs/contracts/data.md (M03)."""
    return (
        CheckConstraint("size_bytes > 0", name=conv("portfolio_uploads_size_bytes_check")),
        CheckConstraint("expires_at > created_at", name=conv("ck_portfolio_uploads_expiry")),
        CheckConstraint("length(filename) > 0", name=conv("portfolio_uploads_filename_check")),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name=conv("ck_portfolio_uploads_sha256")),
    )
