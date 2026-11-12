#!/usr/bin/env bash
# Environment-only configuration. No credential is ever hardcoded or defaulted.
set -euo pipefail

: "${BACKUP_PG_IMAGE:=postgres:16-alpine}"
: "${BACKUP_MC_IMAGE:=quay.io/minio/mc:latest}"
: "${BACKUP_FREEZE:=1}"
: "${BACKUP_KEEP_DAILY:=7}"
: "${BACKUP_KEEP_WEEKLY:=4}"
: "${BACKUP_PGHOST:=db}"
: "${BACKUP_S3_HOST:=minio:9000}"
: "${BACKUP_S3_SCHEME:=http}"

load_backup_config() {
  require_cmd docker sha256sum tar openssl date sed cut id
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
  PG_IMAGE="$BACKUP_PG_IMAGE"; MC_IMAGE="$BACKUP_MC_IMAGE"
  NETWORK="$BACKUP_DOCKER_NETWORK"
  PGHOST="$BACKUP_PGHOST"; PGUSER="$BACKUP_PGUSER"; PGDATABASE="$BACKUP_PGDATABASE"
  export PGPASSWORD="$BACKUP_PGPASSWORD"
  export MC_HOST_s3="${BACKUP_S3_SCHEME}://${BACKUP_S3_ACCESS_KEY}:${BACKUP_S3_SECRET_KEY}@${BACKUP_S3_HOST}"
  PASSPHRASE="$BACKUP_PASSPHRASE"
  BUCKETS=("$BACKUP_QUARANTINE_BUCKET" "$BACKUP_VALIDATED_BUCKET")
  VALIDATED_BUCKET="$BACKUP_VALIDATED_BUCKET"
}

# Restore and verification always target a throwaway stack, never production.
load_restore_config() {
  require_cmd docker sha256sum tar openssl date sed cut id
  require_docker_daemon
  require_env BACKUP_PASSPHRASE RESTORE_DOCKER_NETWORK RESTORE_DB_CONTAINER \
    RESTORE_PGUSER RESTORE_PGDATABASE RESTORE_PGPASSWORD \
    RESTORE_S3_ACCESS_KEY RESTORE_S3_SECRET_KEY \
    RESTORE_QUARANTINE_BUCKET RESTORE_VALIDATED_BUCKET
  : "${RESTORE_PGHOST:=restore-db}"
  : "${RESTORE_S3_HOST:=restore-minio:9000}"
  : "${RESTORE_S3_SCHEME:=http}"
  [ "${RESTORE_CONFIRM_ISOLATED:-}" = "yes" ] ||
    die "set RESTORE_CONFIRM_ISOLATED=yes only for a throwaway stack; production restore is not supported here"
  if [ -n "${BACKUP_DB_CONTAINER:-}" ] && [ "$RESTORE_DB_CONTAINER" = "$BACKUP_DB_CONTAINER" ]; then
    die "RESTORE_DB_CONTAINER equals BACKUP_DB_CONTAINER: refusing to write into the production database"
  fi
  if [ -n "${BACKUP_DOCKER_NETWORK:-}" ] && [ "$RESTORE_DOCKER_NETWORK" = "$BACKUP_DOCKER_NETWORK" ]; then
    die "RESTORE_DOCKER_NETWORK equals BACKUP_DOCKER_NETWORK: refusing to reach production services"
  fi
  PG_IMAGE="$BACKUP_PG_IMAGE"; MC_IMAGE="$BACKUP_MC_IMAGE"
  NETWORK="$RESTORE_DOCKER_NETWORK"
  PGHOST="$RESTORE_PGHOST"; PGUSER="$RESTORE_PGUSER"; PGDATABASE="$RESTORE_PGDATABASE"
  export PGPASSWORD="$RESTORE_PGPASSWORD"
  export MC_HOST_s3="${RESTORE_S3_SCHEME}://${RESTORE_S3_ACCESS_KEY}:${RESTORE_S3_SECRET_KEY}@${RESTORE_S3_HOST}"
  PASSPHRASE="$BACKUP_PASSPHRASE"
  BUCKETS=("$RESTORE_QUARANTINE_BUCKET" "$RESTORE_VALIDATED_BUCKET")
  VALIDATED_BUCKET="$RESTORE_VALIDATED_BUCKET"
}
