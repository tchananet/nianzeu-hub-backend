CREATE TABLE portfolio_uploads (
    id uuid PRIMARY KEY,
    item_id uuid NOT NULL UNIQUE REFERENCES portfolio_items(id) ON DELETE CASCADE,
    quarantine_key varchar(255) NOT NULL UNIQUE CHECK (length(quarantine_key) > 0),
    filename varchar(120) NOT NULL CHECK (length(filename) > 0),
    media_type varchar(80) NOT NULL CHECK (length(media_type) > 0),
    size_bytes bigint NOT NULL,
    sha256 char(64) NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    lease_until timestamptz,
    reservation_active boolean NOT NULL,
    CONSTRAINT ck_portfolio_uploads_size CHECK (size_bytes > 0 AND size_bytes <= 104857600),
    CONSTRAINT ck_portfolio_uploads_sha256 CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_portfolio_uploads_expiry CHECK (expires_at > created_at)
);
