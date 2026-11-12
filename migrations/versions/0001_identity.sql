CREATE TABLE users (
    id uuid PRIMARY KEY,
    email varchar(254) NOT NULL UNIQUE,
    role varchar(16) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_users_email CHECK (email = lower(email) AND length(email) >= 3),
    CONSTRAINT ck_users_role CHECK (role = 'talent')
);
CREATE TABLE credentials (
    user_id uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    password_hash text NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_credentials_password_hash CHECK (length(password_hash) > 0)
);
CREATE TABLE sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash char(64) NOT NULL UNIQUE,
    csrf_token varchar(43) NOT NULL,
    created_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CONSTRAINT ck_sessions_expiry CHECK (expires_at > created_at),
    CONSTRAINT ck_sessions_token_hash CHECK (token_hash ~ '^[0-9a-f]{64}$'),
    CONSTRAINT ck_sessions_csrf CHECK (csrf_token ~ '^[A-Za-z0-9_-]{43}$')
);
CREATE INDEX ix_sessions_user_id_created_at ON sessions(user_id, created_at);
CREATE INDEX ix_sessions_expires_at ON sessions(expires_at);
CREATE TABLE password_reset_tokens (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash char(64) NOT NULL UNIQUE,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    used_at timestamptz,
    CONSTRAINT ck_password_reset_tokens_expiry CHECK (expires_at > created_at),
    CONSTRAINT ck_password_reset_tokens_hash CHECK (token_hash ~ '^[0-9a-f]{64}$')
);
CREATE TABLE rate_limit_windows (
    scope varchar(40) NOT NULL,
    key_hash char(64) NOT NULL,
    window_start timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    count integer NOT NULL CHECK (count >= 0),
    PRIMARY KEY (scope, key_hash, window_start)
);
CREATE INDEX ix_rate_limit_windows_expires_at ON rate_limit_windows(expires_at);
