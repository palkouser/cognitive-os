#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_value COGOS_TEST_DATABASE_URL
require_value COGOS_DATABASE_ADMIN_URL
test_database_name="${COGOS_TEST_DATABASE_URL##*/}"
test_database_name="${test_database_name%%\?*}"
require_test_database "$test_database_name"
export COGOS_DATABASE_URL="$COGOS_TEST_DATABASE_URL"
export COGOS_DATABASE_ADMIN_URL="${COGOS_DATABASE_ADMIN_URL%/*}/$test_database_name"
export COGOS_ARTIFACT_ROOT="${COGOS_TEST_ARTIFACT_ROOT:-/tmp/cognitive-os-artifacts-test}"
cd "$ROOT"
uv run pytest tests/integration/postgres -m postgres -q
