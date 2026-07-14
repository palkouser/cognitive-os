#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cd "$ROOT"
rm -rf dist build
uv build
uv venv "$TMP_DIR/venv" --python 3.12
uv pip install --python "$TMP_DIR/venv/bin/python" dist/*.whl
"$TMP_DIR/venv/bin/python" - <<'PY'
import cognitive_os
import importlib.util

print(f"Installed cognitive_os: {cognitive_os.__file__}")
for optional_module in (
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "opentelemetry.sdk",
    "sympy",
    "z3",
    "pint",
    "inspect_ai",
):
    try:
        installed = importlib.util.find_spec(optional_module) is not None
    except ModuleNotFoundError:
        installed = False
    if installed:
        raise SystemExit(f"Optional module unexpectedly installed: {optional_module}")
PY

if "$TMP_DIR/venv/bin/python" -m zipfile -l dist/*.whl \
  | grep -Eq '(^|/)(LightAgent|tests|docs|\.env|traces)/'; then
  echo "Unexpected repository content found in the wheel."
  exit 1
fi

if tar -tzf dist/*.tar.gz | grep -Eq '/(LightAgent|tests|docs|\.env|traces)/'; then
  echo "Unexpected repository content found in the source distribution."
  exit 1
fi
