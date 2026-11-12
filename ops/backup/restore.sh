#!/usr/bin/env bash
# Restores one backup set into a throwaway stack. Refuses any target that looks
# like production. Reports its own wall-clock duration for RTO measurement.
# Usage: restore.sh <backup-set-directory>
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
for part in config crypto pg objects manifest; do . "$HERE/lib/$part.sh"; done

SET_DIR="${1:-}"
[ -n "$SET_DIR" ] || die "usage: restore.sh <backup-set-directory>"
[ -d "$SET_DIR" ] || die "backup set directory not found: $SET_DIR"
SET_DIR="$(cd -- "$SET_DIR" && pwd)"
load_restore_config

STARTED="$(epoch_now)"
WORK="$(mktemp -d -- "${RESTORE_WORKDIR:-${TMPDIR:-/tmp}}/nianzeuhub-restore.XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT

info "verifying set integrity in $SET_DIR"
( cd -- "$SET_DIR" && sha256sum --quiet -c SHA256SUMS ) ||
  die "SHA256SUMS mismatch: this backup set is corrupted and must not be trusted"

MANIFEST="$SET_DIR/manifest.json"
for key in set_id alembic_revision db_dump_sha256 objects_tar_sha256 \
  quarantine_bucket validated_bucket; do
  manifest_get "$MANIFEST" "$key" >/dev/null
done
[ "$(manifest_get "$MANIFEST" quarantine_bucket)" = "${BUCKETS[0]}" ] ||
  die "RESTORE_QUARANTINE_BUCKET must match the recorded bucket name"
[ "$(manifest_get "$MANIFEST" validated_bucket)" = "$VALIDATED_BUCKET" ] ||
  die "RESTORE_VALIDATED_BUCKET must match the recorded bucket name"

info "restoring set $(manifest_get "$MANIFEST" set_id) (consistency: $(manifest_get "$MANIFEST" consistency))"
decrypt_file "$SET_DIR/db.dump.enc" "$WORK/db.dump"
ACTUAL="$(sha256_of "$WORK/db.dump")"
[ "$ACTUAL" = "$(manifest_get "$MANIFEST" db_dump_sha256)" ] ||
  die "decrypted dump sha256 does not match the manifest: refusing to restore"
pg_dump_toc_ok "$WORK" db.dump

TABLES_PRESENT="$(pg_public_tables_count "$WORK")"
if [ "$TABLES_PRESENT" != 0 ] && [ "${RESTORE_ALLOW_NONEMPTY:-no}" != yes ]; then
  die "target database already has $TABLES_PRESENT public table(s): recreate the throwaway stack"
fi
pg_restore_custom "$WORK" db.dump
info "database restored into $PGDATABASE on $PGHOST"

decrypt_file "$SET_DIR/objects.tar.enc" "$WORK/objects.tar"
ACTUAL="$(sha256_of "$WORK/objects.tar")"
[ "$ACTUAL" = "$(manifest_get "$MANIFEST" objects_tar_sha256)" ] ||
  die "decrypted object archive sha256 does not match the manifest: refusing to restore"
tar --force-local -C "$WORK" -xf "$WORK/objects.tar"
[ -d "$WORK/objects" ] || die "object archive does not contain an objects/ directory"
( cd -- "$WORK" && sha256sum --quiet -c objects.sha256 ) ||
  die "object checksums do not match after extraction: the archive is unusable"

ensure_buckets "$WORK"
mirror_to_storage "$WORK"
RESTORED="$(find "$WORK/objects" -type f | wc -l | tr -d ' ')"
info "objects restored: $RESTORED into buckets ${BUCKETS[*]}"

ELAPSED=$(( $(epoch_now) - STARTED ))
info "restore completed in ${ELAPSED}s; run verify-restore.sh '$SET_DIR' before declaring success"
