DDL = """
CREATE TABLE rate_limit_windows (
    scope varchar(40) NOT NULL,
    key_hash char(64) NOT NULL,
    window_start timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    count integer NOT NULL CHECK (count >= 0),
    PRIMARY KEY (scope, key_hash, window_start)
);
CREATE INDEX ix_rate_limit_windows_expires_at ON rate_limit_windows (expires_at);
CREATE TABLE transaction_probe (id integer PRIMARY KEY);
"""
