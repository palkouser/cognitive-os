#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command psql
for name in COGOS_DATABASE_BOOTSTRAP_URL COGOS_POSTGRES_DATABASE COGOS_POSTGRES_OWNER_USER COGOS_POSTGRES_OWNER_PASSWORD COGOS_POSTGRES_APP_USER COGOS_POSTGRES_APP_PASSWORD; do
  require_value "$name"
done
echo "Bootstrapping roles for database: $COGOS_POSTGRES_DATABASE"
psql "$COGOS_DATABASE_BOOTSTRAP_URL" \
  --set=owner_user="$COGOS_POSTGRES_OWNER_USER" \
  --set=owner_password="$COGOS_POSTGRES_OWNER_PASSWORD" \
  --set=app_user="$COGOS_POSTGRES_APP_USER" \
  --set=app_password="$COGOS_POSTGRES_APP_PASSWORD" \
  --set=database_name="$COGOS_POSTGRES_DATABASE" \
  --file "$ROOT/infra/postgres/bootstrap/roles.sql"
