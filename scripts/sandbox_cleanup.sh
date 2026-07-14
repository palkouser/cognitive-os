#!/usr/bin/env bash
set -euo pipefail
mapfile -t containers < <(docker ps --all --filter label=cogos.managed=true --format '{{.Names}}')
if (( ${#containers[@]} == 0 )); then
  echo "No managed sandbox containers found."
  exit 0
fi
if [[ "${1:-}" != "--confirm" ]]; then
  echo "Refusing cleanup without --confirm." >&2
  exit 2
fi
docker rm --force -- "${containers[@]}"
