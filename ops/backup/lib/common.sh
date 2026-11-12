#!/usr/bin/env bash
# Strictness, logging and preflight helpers shared by every ops/backup script.
# Never prints a secret value: only variable names are ever logged.
set -euo pipefail
umask 077

log() { printf '%s %-5s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "${*:2}" >&2; }
info() { log INFO "$@"; }
warn() { log WARN "$@"; }
die() { log FATAL "$@"; exit 1; }

require_cmd() {
  local c
  for c in "$@"; do
    command -v -- "$c" >/dev/null 2>&1 || die "missing required command: $c"
  done
}

require_env() {
  local n
  for n in "$@"; do
    [ -n "${!n:-}" ] || die "missing required environment variable: $n"
  done
}

# Every PostgreSQL and MinIO access runs in a container: no daemon, no backup.
require_docker_daemon() {
  docker version --format '{{.Server.Version}}' >/dev/null 2>&1 ||
    die 'Docker daemon unreachable: start it before any backup or restore'
}

utc_stamp() { date -u +%Y%m%dT%H%M%SZ; }
epoch_now() { date -u +%s; }

# Refuse destinations that sit inside the production Docker storage.
reject_production_path() {
  [ -n "${1:-}" ] || die "$2 must not be empty"
  case "$1" in
    /var/lib/docker | /var/lib/docker/*) die "$2 must not live inside /var/lib/docker: $1" ;;
  esac
}

sha256_of() { sha256sum -- "$1" | cut -d' ' -f1; }

# Fail when a produced artefact is missing or empty instead of shipping it.
require_nonempty_file() {
  [ -f "$1" ] || die "expected artefact is missing: $1"
  [ -s "$1" ] || die "expected artefact is empty: $1"
}

# Manifest values are machine generated. Rather than escaping, refuse any
# character that would break the flat JSON manifest: loud, not lenient.
json_scalar() {
  local kept
  kept="$(printf '%s' "$1" | tr -d '\42\134\1-\37')"
  [ "$kept" = "$1" ] ||
    die "manifest value for $2 contains a quote, backslash or control character"
  printf '%s' "$1"
}

docker_container_image() {
  docker inspect -f '{{.Config.Image}} {{.Image}}' -- "$1" 2>/dev/null || printf 'unknown'
}

docker_image_digest() {
  docker image inspect -f '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}unpinned{{end}}' \
    -- "$1" 2>/dev/null || printf 'unknown'
}

host_user_flag() { printf -- '%s:%s' "$(id -u)" "$(id -g)"; }
