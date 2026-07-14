#!/usr/bin/env bash
set -euo pipefail
secret_file="${COGOS_PROVIDER_ENV_FILE:-$HOME/.config/cognitive-os/providers.env}"
if [[ ! -f "$secret_file" ]]; then
  echo "Provider secret file not found: $secret_file" >&2
  exit 1
fi
permissions="$(stat -c '%a' "$secret_file")"
if [[ "$permissions" != "600" ]]; then
  echo "Provider secret file must have mode 600." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
source "$secret_file"
set +a
exec "$@"
