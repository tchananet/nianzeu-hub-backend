#!/usr/bin/env bash
# PostgreSQL access through a throwaway client container on the stack network.
# PGPASSWORD is inherited from the environment, never passed as an argument.
set -euo pipefail

pg_run() {
  local mount="$1"; shift
  docker run --rm --network "$NETWORK" --user "$(host_user_flag)" \
    -e PGPASSWORD -v "$mount:/work" -- "$PG_IMAGE" "$@"
}

psql_value() {
  pg_run "$1" psql -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -Atqc "$2"
}

pg_server_version() { psql_value "$1" 'SHOW server_version'; }

# A database without alembic_version is not a restorable service state.
pg_alembic_revision() {
  local rev
  rev="$(psql_value "$1" 'SELECT version_num FROM alembic_version')" ||
    die 'cannot read alembic_version: the database is not a migrated application schema'
  [ -n "$rev" ] || die 'alembic_version is empty: refusing an unidentifiable schema'
  printf '%s' "$rev"
}

pg_table_exists() {
  [ "$(psql_value "$1" "SELECT to_regclass('public.$2') IS NOT NULL")" = t ]
}

pg_public_tables_count() {
  psql_value "$1" \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
}

# Emits "table<TAB>count" lines, "absent" for tables not migrated yet.
# Two round trips only, so the consistency window stays short.
pg_rowcounts() {
  local mount="$1"; shift
  local present query="" t
  present="$(psql_value "$mount" \
    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")"
  for t in "$@"; do
    if printf '%s\n' "$present" | grep -qx -- "$t"; then
      query="$query${query:+ UNION ALL }SELECT '$t', count(*) FROM public.\"$t\""
    else
      printf '%s\tabsent\n' "$t"
    fi
  done
  [ -z "$query" ] || psql_value "$mount" "$query" | tr '|' '\t'
}

pg_dump_custom() {
  local mount="$1" out="$2"
  pg_run "$mount" pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    --format=custom --no-owner --no-privileges --compress=6 --file="/work/$out"
}

# Reads the dump table of contents: detects a truncated or corrupted archive.
pg_dump_toc_ok() {
  docker run --rm --user "$(host_user_flag)" -v "$1:/work:ro" -- "$PG_IMAGE" \
    pg_restore --list "/work/$2" >/dev/null ||
    die "pg_restore --list failed on $2: the dump is truncated or corrupted"
}

pg_restore_custom() {
  local mount="$1" dump="$2"
  pg_run "$mount" pg_restore -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" \
    --no-owner --no-privileges --single-transaction --exit-on-error "/work/$dump"
}
