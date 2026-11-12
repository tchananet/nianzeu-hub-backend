#!/usr/bin/env bash
# Proves a restored throwaway stack is usable: recorded schema revision, row
# counts identical to the backup, and every referenced portfolio object both
# retrievable from storage and matching the sha256 recorded in the database.
# Usage: verify-restore.sh <backup-set-directory>
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
for part in config pg objects manifest schema; do . "$HERE/lib/$part.sh"; done

SET_DIR="${1:-}"
[ -n "$SET_DIR" ] || die "usage: verify-restore.sh <backup-set-directory>"
[ -d "$SET_DIR" ] || die "backup set directory not found: $SET_DIR"
SET_DIR="$(cd -- "$SET_DIR" && pwd)"
load_restore_config
STARTED="$(epoch_now)"
WORK="$(mktemp -d -- "${RESTORE_WORKDIR:-${TMPDIR:-/tmp}}/nianzeuhub-verify.XXXXXX")"
trap 'rm -rf -- "$WORK"' EXIT
MANIFEST="$SET_DIR/manifest.json"

( cd -- "$SET_DIR" && sha256sum --quiet -c SHA256SUMS ) ||
  die "SHA256SUMS mismatch: the reference set is corrupted, verification is meaningless"

EXPECTED_REV="$(manifest_get "$MANIFEST" alembic_revision)"
ACTUAL_REV="$(pg_alembic_revision "$WORK")"
[ "$ACTUAL_REV" = "$EXPECTED_REV" ] ||
  die "restored alembic revision $ACTUAL_REV != recorded $EXPECTED_REV"
info "schema revision verified: $ACTUAL_REV"

pg_rowcounts "$WORK" "${BACKUP_TABLES[@]}" | LC_ALL=C sort > "$WORK/rowcounts.tsv"
diff -u "$SET_DIR/rowcounts.tsv" "$WORK/rowcounts.tsv" ||
  die "restored row counts differ from the backup (left: backup, right: restored)"
info "row counts verified for ${#BACKUP_TABLES[@]} table(s)"

if ! pg_table_exists "$WORK" portfolio_items; then
  [ "${VERIFY_ALLOW_NO_PORTFOLIO:-no}" = yes ] ||
    die "portfolio_items is absent: object verification impossible;"         "set VERIFY_ALLOW_NO_PORTFOLIO=yes only for a pre-O01 schema"
  warn "portfolio_items absent: object/sha256 verification SKIPPED by explicit operator override"
  info "verification finished in $(( $(epoch_now) - STARTED ))s with the portfolio check skipped"
  exit 0
fi

REFERENCED="$(manifest_get "$MANIFEST" referenced_objects)"
psql_value "$WORK" "SELECT object_key || E'\t' || sha256 FROM portfolio_items
  WHERE object_key IS NOT NULL ORDER BY object_key" > "$WORK/objects.list"
CHECKED=0
while IFS="$(printf '\t')" read -r key expected_sha; do
  [ -n "$key" ] || continue
  [ -n "$expected_sha" ] || die "portfolio_items row $key has no recorded sha256"
  stored_object_exists "$VALIDATED_BUCKET" "$key" ||
    die "referenced object is missing from the restored bucket: $key"
  actual_sha="$(stored_object_sha256 "$VALIDATED_BUCKET" "$key")"
  [ "$actual_sha" = "$expected_sha" ] ||
    die "restored object $key has sha256 $actual_sha, database records $expected_sha"
  CHECKED=$((CHECKED + 1))
done < "$WORK/objects.list"

[ "$CHECKED" = "$REFERENCED" ] ||
  die "verified $CHECKED referenced object(s) but the manifest recorded $REFERENCED"
PUBLISHED="$(psql_value "$WORK" \
  "SELECT count(*) FROM portfolio_items WHERE state = 'published'")"
UNPUBLISHED="$(psql_value "$WORK" \
  "SELECT count(*) FROM portfolio_items WHERE state <> 'published' AND object_key IS NOT NULL")"
info "objects verified: $CHECKED retrievable with matching sha256"
info "restored portfolio states: $PUBLISHED published, $UNPUBLISHED validated-not-published"
info "verification passed in $(( $(epoch_now) - STARTED ))s"
