#!/usr/bin/env bash
# Flat one-key-per-line JSON manifest: trivially greppable, no extra tooling.
set -euo pipefail

MANIFEST_SCHEMA=nianzeuhub.backup/1

_mf_str() { printf '  "%s": "%s",\n' "$1" "$(json_scalar "$2" "$1")"; }
_mf_num() { printf '  "%s": %s,\n' "$1" "$2"; }

# manifest_write <path> <key> <value> ... ; numeric values must be bare digits.
manifest_write() {
  local path="$1"; shift
  : > "$path"
  printf '{\n' >> "$path"
  _mf_str schema "$MANIFEST_SCHEMA" >> "$path"
  while [ "$#" -gt 0 ]; do
    [ "$#" -ge 2 ] || die "manifest_write: key $1 has no value"
    case "$2" in
      '' | *[!0-9]*) _mf_str "$1" "$2" >> "$path" ;;
      *) _mf_num "$1" "$2" >> "$path" ;;
    esac
    shift 2
  done
  printf '  "end": true\n}\n' >> "$path"
  require_nonempty_file "$path"
}

manifest_get() {
  local value
  value="$(sed -n "s/^  \"$2\": \"\(.*\)\",\$/\1/p;s/^  \"$2\": \([0-9][0-9]*\),\$/\1/p" "$1")"
  [ -n "$value" ] || die "manifest $1 has no usable value for key: $2"
  printf '%s' "$value"
}
