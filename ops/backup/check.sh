#!/usr/bin/env bash
# Static checks only: parses every script, never connects, never deploys.
set -euo pipefail
cd -- "$(dirname -- "$0")"

status=0
for f in ./*.sh lib/*.sh; do
  if bash -n -- "$f"; then
    printf 'syntax ok   %s\n' "$f"
  else
    printf 'syntax FAIL %s\n' "$f"
    status=1
  fi
done

for f in ./*.sh lib/*.sh; do
  n="$(wc -l < "$f" | tr -d ' ')"
  if [ "$n" -gt 99 ]; then
    printf 'too long    %s (%s lines, limit 99)\n' "$f" "$n"
    status=1
  fi
done

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -S style -- ./*.sh lib/*.sh || status=1
else
  printf 'shellcheck not installed: static lint NOT run (not a pass)\n'
fi

if command -v docker >/dev/null 2>&1; then
  # Placeholder values only: this renders the file, it never deploys it.
  docker compose --env-file backup.env.example -f restore-stack.yaml     config --quiet || status=1
else
  printf 'docker not installed: restore-stack.yaml NOT validated (not a pass)\n'
fi

exit "$status"
