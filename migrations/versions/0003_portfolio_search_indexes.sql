CREATE INDEX ix_talent_profiles_updated_at_id ON talent_profiles (updated_at DESC, id ASC);
CREATE INDEX ix_talent_profiles_availability ON talent_profiles (availability);
CREATE INDEX ix_talent_profiles_experience_level ON talent_profiles (experience_level);
CREATE INDEX ix_talent_profiles_country_city ON talent_profiles (country_code, lower(city));
CREATE INDEX ix_profile_skills_skill_profile ON profile_skills (skill_id, profile_id);
