#!/usr/bin/env bash
# Environment-only configuration. No credential is ever hardcoded or defaulted.
set -euo pipefail

: "${BACKUP_PG_IMAGE:=postgres:16-alpine}"
# S3 client image. Pinned to a release tag, never :latest.
: "${BACKUP_OBJECT_CLIENT_IMAGE:=rclone/rclone:1.76.0}"
: "${BACKUP_FREEZE:=1}"
: "${BACKUP_INCLUDE_QUARANTINE:=0}"
: "${BACKUP_KEEP_DAILY:=7}"
: "${BACKUP_KEEP_WEEKLY:=4}"
: "${BACKUP_PGHOST:=db}"
# host:port of the SeaweedFS S3 gateway, never hardcoded further down.
: "${BACKUP_S3_HOST:=storage:8333}"
: "${BACKUP_S3_SCHEME:=http}"

# Declares the rclone remote "s3" purely through the environment: no config
# file, no credential on a command line, nothing in source control.
# Usage: export_storage_remote <scheme> <host:port> <access-key> <secret-key>
export_storage_remote() {
  export RCLONE_CONFIG_S3_TYPE=s3
  export RCLONE_CONFIG_S3_PROVIDER=Other
  export RCLONE_CONFIG_S3_ENDPOINT="$1://$2"
  export RCLONE_CONFIG_S3_ACCESS_KEY_ID="$3"
  export RCLONE_CONFIG_S3_SECRET_ACCESS_KEY="$4"
}

load_backup_config() {
  require_cmd docker sha256sum tar openssl date sed cut id find du wc grep
  require_docker_daemon
  require_env BACKUP_ROOT BACKUP_PASSPHRASE BACKUP_DOCKER_NETWORK \
    BACKUP_PGUSER BACKUP_PGDATABASE BACKUP_PGPASSWORD \
    BACKUP_S3_ACCESS_KEY BACKUP_S3_SECRET_KEY \
    BACKUP_QUARANTINE_BUCKET BACKUP_VALIDATED_BUCKET
  reject_production_path "$BACKUP_ROOT" BACKUP_ROOT
  case "$BACKUP_FREEZE" in
    1) require_env BACKUP_API_CONTAINER ;;
    0) warn "BACKUP_FREEZE=0: mutations stay live, the backup point is NOT atomic" ;;
    *) die "BACKUP_FREEZE must be 0 or 1, got: $BACKUP_FREEZE" ;;
  esac
  [ "$BACKUP_KEEP_DAILY" -ge 1 ] || die "BACKUP_KEEP_DAILY must be >= 1"
  [ "$BACKUP_KEEP_WEEKLY" -ge 0 ] || die "BACKUP_KEEP_WEEKLY must be >= 0"
  PG_IMAGE="$BACKUP_PG_IMAGE"; OBJECT_CLIENT_IMAGE="$BACKUP_OBJECT_CLIENT_IMAGE"
  NETWORK="$BACKUP_DOCKER_NETWORK"
  PGHOST="$BACKUP_PGHOST"; PGUSER="$BACKUP_PGUSER"; PGDATABASE="$BACKUP_PGDATABASE"
  export PGPASSWORD="$BACKUP_PGPASSWORD"
  export_storage_remote "$BACKUP_S3_SCHEME" "$BACKUP_S3_HOST" \
    "$BACKUP_S3_ACCESS_KEY" "$BACKUP_S3_SECRET_KEY"
  PASSPHRASE="$BACKUP_PASSPHRASE"
  QUARANTINE_BUCKET="$BACKUP_QUARANTINE_BUCKET"
  VALIDATED_BUCKET="$BACKUP_VALIDATED_BUCKET"
  select_buckets "$BACKUP_INCLUDE_QUARANTINE"
}

# The validated bucket is always captured: it holds the immutable final objects
# referenced by portfolio_items.object_key. Quarantine is opt-in only; see
# docs/backup-scope.md for why losing in-flight uploads is accepted.
select_buckets() {
  case "$1" in
    0) BUCKETS=("$VALIDATED_BUCKET") ;;
    1) BUCKETS=("$QUARANTINE_BUCKET" "$VALIDATED_BUCKET") ;;
    *) die "include-quarantine flag must be 0 or 1, got: $1" ;;
  esac
  QUARANTINE_INCLUDED="$1"
}

# Restore and verification always target a throwaway stack, never production.
load_restore_config() {
  require_cmd docker sha256sum tar openssl date sed cut id find du wc grep
  require_docker_daemon
  require_env BACKUP_PASSPHRASE RESTORE_DOCKER_NETWORK RESTORE_DB_CONTAINER \
    RESTORE_PGUSER RESTORE_PGDATABASE RESTORE_PGPASSWORD \
    RESTORE_S3_ACCESS_KEY RESTORE_S3_SECRET_KEY \
    RESTORE_QUARANTINE_BUCKET RESTORE_VALIDATED_BUCKET
  : "${RESTORE_PGHOST:=restore-db}"
  : "${RESTORE_S3_HOST:=restore-storage:8333}"
  : "${RESTORE_S3_SCHEME:=http}"
  [ "${RESTORE_CONFIRM_ISOLATED:-}" = "yes" ] ||
    die "set RESTORE_CONFIRM_ISOLATED=yes only for a throwaway stack;"         "restoring into production is not supported here"
  if [ -n "${BACKUP_DB_CONTAINER:-}" ] && [ "$RESTORE_DB_CONTAINER" = "$BACKUP_DB_CONTAINER" ]; then
    die "RESTORE_DB_CONTAINER equals BACKUP_DB_CONTAINER:"         "refusing to write into the production database"
  fi
  if [ -n "${BACKUP_DOCKER_NETWORK:-}" ] && [ "$RESTORE_DOCKER_NETWORK" = "$BACKUP_DOCKER_NETWORK" ]; then
    die "RESTORE_DOCKER_NETWORK equals BACKUP_DOCKER_NETWORK:"         "refusing to reach production services"
  fi
  PG_IMAGE="$BACKUP_PG_IMAGE"; OBJECT_CLIENT_IMAGE="$BACKUP_OBJECT_CLIENT_IMAGE"
  NETWORK="$RESTORE_DOCKER_NETWORK"
  PGHOST="$RESTORE_PGHOST"; PGUSER="$RESTORE_PGUSER"; PGDATABASE="$RESTORE_PGDATABASE"
  export PGPASSWORD="$RESTORE_PGPASSWORD"
  export_storage_remote "$RESTORE_S3_SCHEME" "$RESTORE_S3_HOST" \
    "$RESTORE_S3_ACCESS_KEY" "$RESTORE_S3_SECRET_KEY"
  PASSPHRASE="$BACKUP_PASSPHRASE"
  QUARANTINE_BUCKET="$RESTORE_QUARANTINE_BUCKET"
  VALIDATED_BUCKET="$RESTORE_VALIDATED_BUCKET"
  select_buckets 0
}
