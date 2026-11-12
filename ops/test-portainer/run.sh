#!/usr/bin/env bash
# Static rendering helper only: never deploys or installs dependencies.
set -euo pipefail
cd -- "$(dirname -- "$0")"
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml config
