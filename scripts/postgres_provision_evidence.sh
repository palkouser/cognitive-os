#!/usr/bin/env bash
# Create the evidence databases a sprint needs, and nothing else.
#
# S21D2-082. Two inherited gaps meet here:
#
#   * no repository command provisions an evidence database, so every sprint since C1 has
#     created them by hand and recorded that as a deviation;
#   * `postgres_bootstrap_roles.sh` runs `ALTER ROLE <owner> LOGIN NOSUPERUSER` against the
#     owner it is connecting as. Where the owner is a superuser the first run silently
#     demotes it and every later run aborts on the same line, half-applied. This script does
#     not touch roles at all: it requires them to exist already and says so when they do not.
#
# The refusal list is the point. `require_test_database` in postgres_common.sh guards only on
# a `_test` suffix, which every evidence database also has — that is how the C3 evidence store
# was truncated twice. Here the target must match the configured sprint prefix, so a name
# outside it cannot be created by a typo in the environment file.
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_command psql
for name in COGOS_DATABASE_BOOTSTRAP_URL COGOS_POSTGRES_OWNER_USER COGOS_POSTGRES_APP_USER \
  COGOS_EVIDENCE_DATABASE_PREFIX; do
  require_value "$name"
done

bootstrap_query() { psql "$COGOS_DATABASE_BOOTSTRAP_URL" -Atqc "$1"; }

for role in "$COGOS_POSTGRES_OWNER_USER" "$COGOS_POSTGRES_APP_USER"; do
  if [[ "$(bootstrap_query "SELECT 1 FROM pg_roles WHERE rolname = '$role'")" != "1" ]]; then
    echo "Role $role does not exist. Create the roles first; this script never alters them." >&2
    exit 1
  fi
  echo "role present: $role"
done

if [[ "$(bootstrap_query "SELECT rolsuper FROM pg_roles WHERE rolname = '$COGOS_POSTGRES_OWNER_USER'")" == "t" ]]; then
  echo "note: $COGOS_POSTGRES_OWNER_USER is a superuser. postgres_bootstrap_roles.sh would"
  echo "note: demote it on its next run and abort on every run after that. Do not run it."
fi

for database in "$@"; do
  case "$database" in
  "$COGOS_EVIDENCE_DATABASE_PREFIX"*) ;;
  *)
    echo "Refusing to create $database: outside prefix $COGOS_EVIDENCE_DATABASE_PREFIX" >&2
    exit 1
    ;;
  esac
  if [[ "$(bootstrap_query "SELECT 1 FROM pg_database WHERE datname = '$database'")" == "1" ]]; then
    echo "exists:  $database"
    continue
  fi
  bootstrap_query "CREATE DATABASE \"$database\" OWNER \"$COGOS_POSTGRES_OWNER_USER\"" >/dev/null
  echo "created: $database"
done
