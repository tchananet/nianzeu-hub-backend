from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.schema import conv


def profile_checks() -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint("length(display_name) > 0",
                        name=conv("talent_profiles_display_name_check")),
        CheckConstraint("length(headline) > 0", name=conv("talent_profiles_headline_check")),
        CheckConstraint("length(city) > 0", name=conv("talent_profiles_city_check")),
        CheckConstraint("country_code ~ '^[A-Z]{2}$'",
                        name=conv("talent_profiles_country_code_check")),
        CheckConstraint("availability IN ('immediate','1-week','freelance','full-time')",
                        name=conv("ck_profiles_availability")),
        CheckConstraint("experience_level IN ('junior','intermediate','senior')",
                        name=conv("ck_profiles_experience")),
        CheckConstraint("""(rate_amount IS NULL AND rate_currency IS NULL AND rate_unit IS NULL)
            OR (rate_amount IS NOT NULL AND rate_currency IS NOT NULL AND rate_unit IS NOT NULL
                AND rate_amount > 0 AND rate_amount <= 99999999.99
                AND rate_amount = trunc(rate_amount) AND rate_currency = 'XAF'
                AND rate_unit IN ('hour', 'day', 'project'))""", name=conv("ck_profiles_rate")),
    )


def experience_checks() -> tuple[CheckConstraint | UniqueConstraint, ...]:
    return (
        CheckConstraint("length(title) > 0", name=conv("experiences_title_check")),
        CheckConstraint("length(organization) > 0", name=conv("experiences_organization_check")),
        CheckConstraint("position BETWEEN 0 AND 19", name=conv("experiences_position_check")),
        CheckConstraint("end_date IS NULL OR end_date >= start_date",
                        name=conv("ck_experiences_dates")),
        UniqueConstraint("profile_id", "position", name="experiences_profile_id_position_key"),
    )


def certification_checks() -> tuple[CheckConstraint | UniqueConstraint, ...]:
    return (
        CheckConstraint("length(name) > 0", name=conv("certifications_name_check")),
        CheckConstraint("length(issuer) > 0", name=conv("certifications_issuer_check")),
        CheckConstraint("position BETWEEN 0 AND 19", name=conv("certifications_position_check")),
        CheckConstraint("credential_url IS NULL OR length(credential_url) > 0",
                        name=conv("certifications_credential_url_check")),
        CheckConstraint("expires_on IS NULL OR expires_on >= issued_on",
                        name=conv("ck_certifications_dates")),
        UniqueConstraint("profile_id", "position", name="certifications_profile_id_position_key"),
    )
