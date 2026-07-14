#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_ENV_FILE="${COGOS_POSTGRES_ENV_FILE:-$ROOT/.env.postgres.local}"

load_postgres_environment() {
  if [[ ! -f "$POSTGRES_ENV_FILE" ]]; then
    echo "PostgreSQL environment file not found: $POSTGRES_ENV_FILE" >&2
    echo "Copy .env.postgres.example to .env.postgres.local and set private values." >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$POSTGRES_ENV_FILE"
  set +a
}

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "$name must be set." >&2
    exit 1
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command is unavailable: $1" >&2
    exit 1
  }
}

require_test_database() {
  local database_name="$1"
  if [[ -z "$database_name" || "$database_name" != *_test ]]; then
    echo "Refusing destructive operation on non-test database: $database_name" >&2
    exit 1
  fi
  echo "Target test database: $database_name"
}
