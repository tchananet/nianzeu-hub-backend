#!/usr/bin/env bash
# Tables whose row counts are recorded and compared, per docs/contracts/data.md.
# A table absent from the database is reported as "absent", never silently
# skipped: the backup and the restore must agree on the migrated schema.
set -euo pipefail

BACKUP_TABLES=(
  users
  credentials
  sessions
  password_reset_tokens
  rate_limit_windows
  talent_profiles
  skills
  profile_skills
  experiences
  certifications
  contact_settings
  profile_views
  profile_view_dedup
  portfolio_items
  portfolio_uploads
)
