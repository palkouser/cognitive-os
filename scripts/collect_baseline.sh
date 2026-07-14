#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/docs/baseline/generated"
mkdir -p "$OUT"

{
  date --iso-8601=seconds
  uname -a
  lsb_release -a
} >"$OUT/system.txt" 2>&1

{
  findmnt /home/palkouser/projekt
  df -hT /home/palkouser/projekt
  lsblk -o NAME,SIZE,FSTYPE,FSAVAIL,FSUSE%,MOUNTPOINTS,MODEL
} >"$OUT/storage.txt" 2>&1

nvidia-smi >"$OUT/nvidia-smi.txt" 2>&1 || true
git -C "$ROOT" remote -v >"$OUT/git-remotes.txt"
git -C "$ROOT" rev-parse HEAD >"$OUT/git-head.txt"
git -C "$ROOT" status --short >"$OUT/git-status.txt"
uv --version >"$OUT/uv-version.txt"
uv run python --version >"$OUT/python-version.txt" 2>&1
uv pip list >"$OUT/python-packages.txt"
