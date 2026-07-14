#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command docker
docker compose --env-file "$POSTGRES_ENV_FILE" -f "$ROOT/infra/compose/postgres.yml" down
