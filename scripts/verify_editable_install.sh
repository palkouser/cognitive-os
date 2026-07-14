#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

uv venv "$TMP_DIR/venv" --python 3.12
uv pip install --python "$TMP_DIR/venv/bin/python" --editable "$ROOT"
"$TMP_DIR/venv/bin/python" - <<'PY'
from pathlib import Path

import cognitive_os

module_path = Path(cognitive_os.__file__).resolve()
if "src/cognitive_os" not in module_path.as_posix():
    raise SystemExit(f"Unexpected cognitive_os import location: {module_path}")
print(f"Editable import OK: {module_path}")
PY
