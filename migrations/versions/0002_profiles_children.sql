CREATE TABLE experiences (
    id uuid PRIMARY KEY,
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    title varchar(150) NOT NULL CHECK (length(title) > 0),
    organization varchar(150) NOT NULL CHECK (length(organization) > 0),
    description varchar(2000) NOT NULL,
    start_date date NOT NULL,
    end_date date,
    position smallint NOT NULL CHECK (position BETWEEN 0 AND 19),
    created_at timestamptz NOT NULL,
    UNIQUE (profile_id, position),
    CONSTRAINT ck_experiences_dates CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE TABLE certifications (
    id uuid PRIMARY KEY,
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    name varchar(150) NOT NULL CHECK (length(name) > 0),
    issuer varchar(150) NOT NULL CHECK (length(issuer) > 0),
    issued_on date NOT NULL,
    expires_on date,
    credential_url varchar(2048) CHECK (credential_url IS NULL OR length(credential_url) > 0),
    position smallint NOT NULL CHECK (position BETWEEN 0 AND 19),
    created_at timestamptz NOT NULL,
    UNIQUE (profile_id, position),
    CONSTRAINT ck_certifications_dates CHECK (expires_on IS NULL OR expires_on >= issued_on)
);
