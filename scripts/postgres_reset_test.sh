#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command psql
require_value COGOS_TEST_DATABASE_URL
database_name="$(psql "$COGOS_TEST_DATABASE_URL" -Atqc 'SELECT current_database()')"
require_test_database "$database_name"
psql "$COGOS_TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -c \
  'TRUNCATE cognitive_os.artifacts, cognitive_os.artifact_blobs, cognitive_os.events, cognitive_os.event_streams RESTART IDENTITY CASCADE'
