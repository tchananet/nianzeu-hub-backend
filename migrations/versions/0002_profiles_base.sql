CREATE TABLE talent_profiles (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    display_name varchar(100) NOT NULL CHECK (length(display_name) > 0),
    headline varchar(160) NOT NULL CHECK (length(headline) > 0),
    bio varchar(5000) NOT NULL,
    city varchar(100) NOT NULL CHECK (length(city) > 0),
    country_code char(2) NOT NULL CHECK (country_code ~ '^[A-Z]{2}$'),
    availability varchar(16) NOT NULL,
    experience_level varchar(16) NOT NULL,
    rate_amount numeric(10,2),
    rate_currency char(3),
    rate_unit varchar(10),
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT ck_profiles_availability CHECK (
        availability IN ('immediate', '1-week', 'freelance', 'full-time')
    ),
    CONSTRAINT ck_profiles_experience CHECK (
        experience_level IN ('junior', 'intermediate', 'senior')
    ),
    CONSTRAINT ck_profiles_rate CHECK (
        (rate_amount IS NULL AND rate_currency IS NULL AND rate_unit IS NULL)
        OR (rate_amount IS NOT NULL AND rate_currency IS NOT NULL AND rate_unit IS NOT NULL
            AND rate_amount > 0 AND rate_amount <= 99999999.99
            AND rate_amount = trunc(rate_amount) AND rate_currency = 'XAF'
            AND rate_unit IN ('hour', 'day', 'project'))
    )
);
CREATE TABLE skills (
    id uuid PRIMARY KEY,
    name varchar(80) NOT NULL CHECK (length(name) > 0),
    normalized_name varchar(80) NOT NULL UNIQUE,
    CONSTRAINT ck_skills_normalized CHECK (normalized_name = lower(name))
);
CREATE TABLE profile_skills (
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    skill_id uuid NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
    PRIMARY KEY (profile_id, skill_id)
);
