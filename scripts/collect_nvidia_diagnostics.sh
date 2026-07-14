#!/usr/bin/env bash
set -euo pipefail

phase="${1:-before}"
case "$phase" in
  before|after) ;;
  *) printf 'Usage: %s [before|after]\n' "$0" >&2; exit 2 ;;
esac

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/docs/baseline/generated/nvidia-diagnostics-$phase.txt"
mkdir -p "$(dirname "$out")"

{
  date --iso-8601=seconds
  printf '=== PCI ===\n'
  lspci -nnk | grep -A4 -Ei 'VGA|3D|NVIDIA' || true
  printf '\n=== nvidia-smi ===\n'
  nvidia-smi || true
  printf '\n=== modules ===\n'
  lsmod | grep -E 'nvidia|nouveau' || true
  printf '\n=== DKMS ===\n'
  command -v dkms >/dev/null && dkms status || true
  printf '\n=== Secure Boot ===\n'
  command -v mokutil >/dev/null && mokutil --sb-state || true
  printf '\n=== installed NVIDIA packages ===\n'
  dpkg -l | grep -E '^ii.*nvidia' || true
  printf '\n=== recommended drivers ===\n'
  command -v ubuntu-drivers >/dev/null && ubuntu-drivers devices || true
  printf '\n=== kernel messages ===\n'
  journalctl -k -b | grep -Ei \
    'nvidia|nouveau|NVRM|module verification|secure boot' || true
} >"$out" 2>&1

printf 'Wrote %s\n' "$out"
