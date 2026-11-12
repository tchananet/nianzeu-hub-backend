#!/usr/bin/env bash
# Consistency window: the API container owns every mutation and the hourly
# portfolio cleanup, so stopping it suspends both for the whole snapshot.
set -euo pipefail

FREEZE_HELD=0
FREEZE_STARTED_AT=0
FREEZE_SECONDS=0
CONSISTENCY_MODE=unset

container_running() {
  [ "$(docker inspect -f '{{.State.Running}}' -- "$1" 2>/dev/null || printf false)" = true ]
}

freeze_begin() {
  if [ "$BACKUP_FREEZE" != 1 ]; then
    CONSISTENCY_MODE=online-nonatomic
    warn "no freeze: database and objects are captured while writes continue"
    warn "the inconsistency window is the whole run; see docs/backup.md"
    return 0
  fi
  container_running "$BACKUP_API_CONTAINER" ||
    die "API container $BACKUP_API_CONTAINER is not running:"         "refusing a backup of an unknown service state"
  FREEZE_STARTED_AT="$(epoch_now)"
  info "freezing mutations: stopping $BACKUP_API_CONTAINER"
  docker stop --time 30 -- "$BACKUP_API_CONTAINER" >/dev/null ||
    die "cannot stop $BACKUP_API_CONTAINER: aborting before any snapshot"
  if container_running "$BACKUP_API_CONTAINER"; then
    die "$BACKUP_API_CONTAINER is still running after stop: refusing an inconsistent snapshot"
  fi
  FREEZE_HELD=1
  CONSISTENCY_MODE=frozen-api
}

freeze_end() {
  [ "$FREEZE_HELD" = 1 ] || return 0
  FREEZE_HELD=0
  FREEZE_SECONDS=$(( $(epoch_now) - FREEZE_STARTED_AT ))
  info "releasing mutations: starting $BACKUP_API_CONTAINER after ${FREEZE_SECONDS}s"
  docker start -- "$BACKUP_API_CONTAINER" >/dev/null ||
    die "CRITICAL: $BACKUP_API_CONTAINER could not be restarted;"         "the service stays down until an operator acts"
}
