#!/usr/bin/env bash
# MinIO object access through a throwaway mc container on the stack network.
# Credentials travel only in MC_HOST_s3, inherited from the environment.
set -euo pipefail

_mc_base() {
  printf '%s\n' --rm --network "$NETWORK" --user "$(host_user_flag)" \
    -e MC_HOST_s3 -e HOME=/tmp --entrypoint mc
}

mc_run() {
  local mount="$1"; shift
  local -a base; mapfile -t base < <(_mc_base)
  docker run "${base[@]}" -v "$mount:/work" -- "$MC_IMAGE" \
    --config-dir /tmp/mc --no-color --quiet "$@"
}

# Streams object bytes to stdout without touching the host filesystem.
mc_stream() {
  local -a base; mapfile -t base < <(_mc_base)
  docker run "${base[@]}" -- "$MC_IMAGE" --config-dir /tmp/mc --no-color --quiet "$@"
}

ensure_buckets() {
  local b
  for b in "${BUCKETS[@]}"; do
    mc_run "$1" mb --ignore-existing "s3/$b" || die "cannot create bucket $b"
  done
}

# Pulls every object of every bucket into <stage>/objects/<bucket>/<key>.
mirror_from_storage() {
  local stage="$1" b
  for b in "${BUCKETS[@]}"; do
    mkdir -p -- "$stage/objects/$b"
    mc_run "$stage" mirror --overwrite "s3/$b" "/work/objects/$b" ||
      die "mirror from bucket $b failed"
  done
}

mirror_to_storage() {
  local stage="$1" b
  for b in "${BUCKETS[@]}"; do
    [ -d "$stage/objects/$b" ] || die "restored set has no staged directory for bucket $b"
    mc_run "$stage" mirror --overwrite "/work/objects/$b" "s3/$b" ||
      die "mirror into bucket $b failed"
  done
}

object_count() { find "$1/objects" -type f | wc -l | tr -d ' '; }
object_bytes() { du -sb -- "$1/objects" | cut -f1; }

# sha256 of a single stored object, read back through the storage API.
stored_object_sha256() {
  local out
  out="$(mc_stream cat "s3/$1/$2" | sha256sum | cut -d' ' -f1)" ||
    die "object is not retrievable from bucket $1: $2"
  printf '%s' "$out"
}

stored_object_exists() {
  mc_stream stat "s3/$1/$2" >/dev/null 2>&1
}
