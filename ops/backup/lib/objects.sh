#!/usr/bin/env bash
# SeaweedFS S3 access through a throwaway rclone container on the stack network.
# The remote named "s3" is declared entirely by the RCLONE_CONFIG_S3_* variables
# exported by lib/config.sh, so no credential ever reaches a config file, a
# command line or a log. --config /dev/null forbids reading any config file.
set -euo pipefail

_storage_base() {
  printf '%s\n' --rm --network "$NETWORK" --user "$(host_user_flag)" \
    -e RCLONE_CONFIG_S3_TYPE -e RCLONE_CONFIG_S3_PROVIDER \
    -e RCLONE_CONFIG_S3_ENDPOINT -e RCLONE_CONFIG_S3_ACCESS_KEY_ID \
    -e RCLONE_CONFIG_S3_SECRET_ACCESS_KEY -e HOME=/tmp --entrypoint rclone
}

_storage_flags() { printf '%s\n' --config /dev/null --log-level NOTICE; }

storage_run() {
  local mount="$1"; shift
  local -a base flags
  mapfile -t base < <(_storage_base)
  mapfile -t flags < <(_storage_flags)
  docker run "${base[@]}" -v "$mount:/work" -- "$OBJECT_CLIENT_IMAGE" \
    "${flags[@]}" "$@"
}

# Streams object bytes to stdout without touching the host filesystem.
storage_stream() {
  local -a base flags
  mapfile -t base < <(_storage_base)
  mapfile -t flags < <(_storage_flags)
  docker run "${base[@]}" -- "$OBJECT_CLIENT_IMAGE" "${flags[@]}" "$@"
}

# Both buckets must exist for the application to pass readiness, even when the
# restored set carries objects for only one of them. rclone mkdir tolerates an
# existing bucket, so this stays idempotent.
ensure_buckets() {
  local mount="$1" b; shift
  for b in "$@"; do
    storage_run "$mount" mkdir "s3:$b" || die "cannot create bucket $b"
  done
}

# Pulls every object of every bucket into <stage>/objects/<bucket>/<key>.
# `copy` adds and updates but never deletes, which is what the warm pre-copy
# plus incremental second pass relies on; `--checksum` compares content rather
# than trusting the modification times a mirrored object carries.
mirror_from_storage() {
  local stage="$1" b
  for b in "${BUCKETS[@]}"; do
    mkdir -p -- "$stage/objects/$b"
    storage_run "$stage" copy --checksum "s3:$b" "/work/objects/$b" ||
      die "copy from bucket $b failed"
  done
}

mirror_to_storage() {
  local stage="$1" b
  for b in "${BUCKETS[@]}"; do
    [ -d "$stage/objects/$b" ] || die "restored set has no staged directory for bucket $b"
    storage_run "$stage" copy --checksum "/work/objects/$b" "s3:$b" ||
      die "copy into bucket $b failed"
  done
}

object_count() { find "$1/objects" -type f | wc -l | tr -d ' '; }
object_bytes() { du -sb -- "$1/objects" | cut -f1; }

# sha256 of a single stored object, read back through the storage API.
stored_object_sha256() {
  local out
  out="$(storage_stream cat "s3:$1/$2" | sha256sum | cut -d' ' -f1)" ||
    die "object is not retrievable from bucket $1: $2"
  printf '%s' "$out"
}

# True only when the key resolves to a real object. A missing key makes rclone
# exit non-zero; the IsDir test also rejects a prefix that merely looks like one.
stored_object_exists() {
  local out
  out="$(storage_stream lsjson --stat "s3:$1/$2" 2>/dev/null)" || return 1
  printf '%s' "$out" | grep -q '"IsDir"[[:space:]]*:[[:space:]]*false'
}
