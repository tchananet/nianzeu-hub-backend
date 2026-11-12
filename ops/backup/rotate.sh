#!/usr/bin/env bash
# Retention: keep the newest set of each of the last BACKUP_KEEP_DAILY days and
# of each of the last BACKUP_KEEP_WEEKLY ISO weeks. Everything else is deleted.
# --dry-run reports the decision without touching anything.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
. "$HERE/lib/config.sh"

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  '') ;;
  *) die "usage: rotate.sh [--dry-run]" ;;
esac

require_cmd date find sort
require_env BACKUP_ROOT
reject_production_path "$BACKUP_ROOT" BACKUP_ROOT
[ -d "$BACKUP_ROOT" ] || die "BACKUP_ROOT does not exist: $BACKUP_ROOT"

# Set directories are named with a UTC stamp, so lexical order is chronological.
mapfile -t SETS < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d \
  -name '????????T??????Z' -printf '%f\n' | LC_ALL=C sort -r)
TOTAL="${#SETS[@]}"
[ "$TOTAL" -gt 0 ] || die "no backup set found under $BACKUP_ROOT: nothing to rotate"
info "rotation over $TOTAL set(s), keep ${BACKUP_KEEP_DAILY} daily + ${BACKUP_KEEP_WEEKLY} weekly"

if [ "$TOTAL" -le "$BACKUP_KEEP_DAILY" ]; then
  info "fewer sets than the daily retention target: nothing is deleted"
  exit 0
fi

set_key() { printf '%s-%s-%s' "${1:0:4}" "${1:4:2}" "${1:6:2}"; }
iso_week() { date -u -d "$(set_key "$1")" +%G-%V; }

declare -A DAY_SEEN=() WEEK_SEEN=()
DAILY_KEPT=0
WEEKLY_KEPT=0
KEEP=()
DROP=()
for s in "${SETS[@]}"; do
  day="$(set_key "$s")"
  week="$(iso_week "$s")" || die "cannot parse the date of set $s"
  if [ -z "${DAY_SEEN[$day]:-}" ] && [ "$DAILY_KEPT" -lt "$BACKUP_KEEP_DAILY" ]; then
    DAY_SEEN[$day]=1; WEEK_SEEN[$week]=1
    DAILY_KEPT=$((DAILY_KEPT + 1)); KEEP+=("$s daily")
  elif [ -z "${WEEK_SEEN[$week]:-}" ] && [ "$WEEKLY_KEPT" -lt "$BACKUP_KEEP_WEEKLY" ]; then
    WEEK_SEEN[$week]=1
    WEEKLY_KEPT=$((WEEKLY_KEPT + 1)); KEEP+=("$s weekly")
  else
    DROP+=("$s")
  fi
done

[ "${#KEEP[@]}" -gt 0 ] || die "rotation would keep no set at all: refusing to delete anything"
for k in "${KEEP[@]}"; do info "keep $k"; done
for d in "${DROP[@]}"; do
  if [ "$DRY_RUN" = 1 ]; then
    info "would delete $d"
  else
    info "delete $d"
    rm -rf -- "$BACKUP_ROOT/$d"
  fi
done
[ "$DRY_RUN" = 1 ] && VERB=selected || VERB=deleted
info "rotation done: ${#KEEP[@]} kept, ${#DROP[@]} $VERB"
