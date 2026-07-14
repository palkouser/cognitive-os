#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command docker
for _ in $(seq 1 60); do
  status="$(docker compose --env-file "$POSTGRES_ENV_FILE" -f "$ROOT/infra/compose/postgres.yml" ps --format json postgres 2>/dev/null || true)"
  if [[ "$status" == *'healthy'* ]]; then
    echo "PostgreSQL is healthy."
    exit 0
  fi
  sleep 1
done
echo "PostgreSQL did not become healthy within 60 seconds." >&2
exit 1
