#!/usr/bin/env bash
# Creates one encrypted, self-describing backup set: PostgreSQL dump plus every
# MinIO object, captured at a single consistent point. Exits non-zero on any
# doubt; a partially written set is removed instead of being published.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
for part in config crypto pg objects freeze manifest schema; do
  . "$HERE/lib/$part.sh"
done

load_backup_config
mkdir -p -- "$BACKUP_ROOT"
SET_ID="$(utc_stamp)"
SET_DIR="$BACKUP_ROOT/$SET_ID"
if [ -e "$SET_DIR" ]; then die "backup set already exists: $SET_DIR"; fi
STAGE="$(mktemp -d -- "$BACKUP_ROOT/.staging.XXXXXX")"
PUBLISHED=0

cleanup() {
  local code=$?
  freeze_end
  rm -rf -- "$STAGE"
  if [ "$PUBLISHED" != 1 ] && [ -d "$SET_DIR" ]; then
    warn "removing incomplete backup set $SET_DIR"
    rm -rf -- "$SET_DIR"
  fi
  [ "$code" -eq 0 ] || log FATAL "backup failed with exit code $code"
  exit "$code"
}
trap cleanup EXIT

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
info "backup set $SET_ID starting"
freeze_begin
[ "$CONSISTENCY_MODE" = frozen-api ] || mirror_from_storage "$STAGE"

ALEMBIC_REVISION="$(pg_alembic_revision "$STAGE")"
PG_VERSION="$(pg_server_version "$STAGE")"
EXPECTED_OBJECTS=0
if pg_table_exists "$STAGE" portfolio_items; then
  EXPECTED_OBJECTS="$(psql_value "$STAGE" \
    'SELECT count(*) FROM portfolio_items WHERE object_key IS NOT NULL')"
fi
pg_rowcounts "$STAGE" "${BACKUP_TABLES[@]}" | LC_ALL=C sort > "$STAGE/rowcounts.tsv"
require_nonempty_file "$STAGE/rowcounts.tsv"

pg_dump_custom "$STAGE" db.dump
require_nonempty_file "$STAGE/db.dump"
pg_dump_toc_ok "$STAGE" db.dump
mirror_from_storage "$STAGE"
freeze_end

VALIDATED_OBJECTS="$(find "$STAGE/objects/$VALIDATED_BUCKET" -type f | wc -l | tr -d ' ')"
[ "$VALIDATED_OBJECTS" -ge "$EXPECTED_OBJECTS" ] ||
  die "captured $VALIDATED_OBJECTS validated objects for $EXPECTED_OBJECTS referenced rows: incomplete backup"
( cd -- "$STAGE" && find objects -type f -print0 | LC_ALL=C sort -z |
  xargs -0 -r sha256sum > objects.sha256 )
tar --force-local -C "$STAGE" -cf "$STAGE/objects.tar" objects objects.sha256
require_nonempty_file "$STAGE/objects.tar"

DB_SHA="$(sha256_of "$STAGE/db.dump")"
TAR_SHA="$(sha256_of "$STAGE/objects.tar")"
mkdir -p -- "$SET_DIR"
encrypt_file "$STAGE/db.dump" "$SET_DIR/db.dump.enc"
encrypt_file "$STAGE/objects.tar" "$SET_DIR/objects.tar.enc"
roundtrip_check "$SET_DIR/db.dump.enc" "$DB_SHA" "$STAGE"
roundtrip_check "$SET_DIR/objects.tar.enc" "$TAR_SHA" "$STAGE"
cp -- "$STAGE/rowcounts.tsv" "$STAGE/objects.sha256" "$SET_DIR/"

manifest_write "$SET_DIR/manifest.json" \
  set_id "$SET_ID" started_at "$STARTED_AT" finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  consistency "$CONSISTENCY_MODE" freeze_seconds "$FREEZE_SECONDS" \
  alembic_revision "$ALEMBIC_REVISION" app_version "${BACKUP_APP_VERSION:-unrecorded}" \
  api_image "$(docker_container_image "${BACKUP_API_CONTAINER:-none}")" \
  pg_server_version "$PG_VERSION" pg_image "$(docker_image_digest "$PG_IMAGE")" \
  mc_image "$(docker_image_digest "$MC_IMAGE")" database "$PGDATABASE" \
  quarantine_bucket "${BUCKETS[0]}" validated_bucket "$VALIDATED_BUCKET" \
  objects_total "$(object_count "$STAGE")" objects_bytes "$(object_bytes "$STAGE")" \
  validated_objects "$VALIDATED_OBJECTS" referenced_objects "$EXPECTED_OBJECTS" \
  db_dump_sha256 "$DB_SHA" objects_tar_sha256 "$TAR_SHA"

( cd -- "$SET_DIR" && sha256sum -- manifest.json rowcounts.tsv objects.sha256 \
  db.dump.enc objects.tar.enc > SHA256SUMS )
( cd -- "$SET_DIR" && sha256sum --quiet -c SHA256SUMS ) || die "set checksum verification failed"
PUBLISHED=1
info "backup set published: $SET_DIR"
"$HERE/rotate.sh"
