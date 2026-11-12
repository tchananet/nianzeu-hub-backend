CREATE TABLE portfolio_items (
    id uuid PRIMARY KEY,
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    title varchar(160) NOT NULL CHECK (length(title) > 0),
    description varchar(2000) NOT NULL,
    type varchar(8) NOT NULL,
    state varchar(12) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    validated_at timestamptz,
    published_at timestamptz,
    object_key varchar(255) UNIQUE CHECK (object_key IS NULL OR length(object_key) > 0),
    filename varchar(120) CHECK (filename IS NULL OR length(filename) > 0),
    media_type varchar(80) CHECK (media_type IS NULL OR length(media_type) > 0),
    size_bytes bigint,
    sha256 char(64),
    rejection_code varchar(40) CHECK (rejection_code IS NULL OR length(rejection_code) > 0),
    CONSTRAINT ck_portfolio_items_type CHECK (type IN ('image', 'pdf', 'video')),
    CONSTRAINT ck_portfolio_items_state CHECK (
        state IN ('draft', 'pending', 'validating', 'rejected', 'validated', 'published')
    ),
    CONSTRAINT ck_portfolio_items_size CHECK (
        size_bytes IS NULL OR (size_bytes >= 1 AND size_bytes <= 104857600)
    ),
    CONSTRAINT ck_portfolio_items_sha256 CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_portfolio_items_final_metadata CHECK (
        CASE WHEN state IN ('validated', 'published') THEN
            object_key IS NOT NULL AND filename IS NOT NULL AND media_type IS NOT NULL
            AND size_bytes IS NOT NULL AND sha256 IS NOT NULL AND validated_at IS NOT NULL
        ELSE
            object_key IS NULL AND filename IS NULL AND media_type IS NULL
            AND size_bytes IS NULL AND sha256 IS NULL AND validated_at IS NULL
        END
    ),
    CONSTRAINT ck_portfolio_items_published_at CHECK (
        (state = 'published') = (published_at IS NOT NULL)
    )
);
CREATE INDEX ix_portfolio_items_profile_state_published
    ON portfolio_items (profile_id, state, published_at, id);
