CREATE TABLE contact_settings (
    profile_id uuid PRIMARY KEY REFERENCES talent_profiles(id) ON DELETE CASCADE,
    email varchar(254) CHECK (email IS NULL OR length(email) > 0),
    phone varchar(16) CHECK (phone IS NULL OR length(phone) > 0),
    whatsapp varchar(16) CHECK (whatsapp IS NULL OR length(whatsapp) > 0),
    email_visible boolean NOT NULL DEFAULT false,
    phone_visible boolean NOT NULL DEFAULT false,
    whatsapp_visible boolean NOT NULL DEFAULT false,
    CONSTRAINT ck_contact_email CHECK (NOT email_visible OR email IS NOT NULL),
    CONSTRAINT ck_contact_phone CHECK (NOT phone_visible OR phone IS NOT NULL),
    CONSTRAINT ck_contact_whatsapp CHECK (NOT whatsapp_visible OR whatsapp IS NOT NULL)
);
CREATE TABLE profile_views (
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    day date NOT NULL,
    count integer NOT NULL CHECK (count >= 0),
    PRIMARY KEY (profile_id, day)
);
CREATE TABLE profile_view_dedup (
    profile_id uuid NOT NULL REFERENCES talent_profiles(id) ON DELETE CASCADE,
    day date NOT NULL,
    visitor_hash char(64) NOT NULL,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (profile_id, day, visitor_hash)
);
CREATE INDEX ix_profile_view_dedup_expires_at ON profile_view_dedup(expires_at);
