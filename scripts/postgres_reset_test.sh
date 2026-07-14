#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command psql
require_value COGOS_TEST_DATABASE_URL
require_value COGOS_DATABASE_ADMIN_URL
database_name="${COGOS_TEST_DATABASE_URL##*/}"
database_name="${database_name%%\?*}"
require_test_database "$database_name"
admin_url="${COGOS_DATABASE_ADMIN_URL%/*}/$database_name"
psql_url="${admin_url/postgresql+asyncpg:/postgresql:}"
psql "$psql_url" -v ON_ERROR_STOP=1 -c \
  'TRUNCATE cognitive_os.artifacts, cognitive_os.artifact_blobs, cognitive_os.events, cognitive_os.event_streams RESTART IDENTITY CASCADE'
