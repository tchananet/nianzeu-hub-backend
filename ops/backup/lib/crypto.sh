#!/usr/bin/env bash
# Symmetric encryption of backup artefacts. The passphrase is passed on a
# dedicated file descriptor, never on the command line and never logged.
set -euo pipefail

: "${BACKUP_PBKDF2_ITER:=600000}"

_openssl_enc() {
  local mode="$1" src="$2" dst="$3"
  printf '%s' "$PASSPHRASE" | openssl enc "$mode" -aes-256-cbc -md sha512 \
    -pbkdf2 -iter "$BACKUP_PBKDF2_ITER" -salt -pass stdin -in "$src" -out "$dst"
}

encrypt_file() {
  local src="$1" dst="$2"
  require_nonempty_file "$src"
  _openssl_enc -e "$src" "$dst"
  require_nonempty_file "$dst"
}

decrypt_file() {
  local src="$1" dst="$2"
  require_nonempty_file "$src"
  _openssl_enc -d "$src" "$dst" ||
    die "decryption failed for $src: wrong BACKUP_PASSPHRASE or corrupted artefact"
  require_nonempty_file "$dst"
}

# Proves the ciphertext is actually recoverable before the backup is accepted.
# The probe lands in the caller's work directory so its cleanup trap removes it.
roundtrip_check() {
  local cipher="$1" expected_sha="$2" workdir="$3"
  local probe="$workdir/roundtrip.probe" actual
  decrypt_file "$cipher" "$probe"
  actual="$(sha256_of "$probe")"
  rm -f -- "$probe"
  [ "$actual" = "$expected_sha" ] ||
    die "round-trip check failed for $cipher: plaintext sha256 $actual != $expected_sha"
  info "round-trip verified: $(basename -- "$cipher")"
}
