#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
require_value COGOS_ARTIFACT_ROOT
if [[ ! -d "$COGOS_ARTIFACT_ROOT" ]]; then
  echo "Artifact root does not exist: $COGOS_ARTIFACT_ROOT" >&2
  exit 1
fi
find "$COGOS_ARTIFACT_ROOT/sha256" -type f ! -name '*.tmp' -print0 2>/dev/null \
  | while IFS= read -r -d '' path; do
      expected="$(basename "$path")"
      actual="$(sha256sum "$path" | cut -d ' ' -f 1)"
      [[ "$actual" == "$expected" ]] || {
        echo "Artifact integrity failure: ${path#"$COGOS_ARTIFACT_ROOT/"}" >&2
        exit 1
      }
    done
echo "Artifact filesystem verification passed."
