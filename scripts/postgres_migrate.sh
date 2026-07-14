#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_value COGOS_DATABASE_ADMIN_URL
cd "$ROOT"
uv run alembic -c infra/postgres/alembic.ini upgrade head
