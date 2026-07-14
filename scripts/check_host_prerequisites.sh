#!/usr/bin/env bash
set -euo pipefail

required_packages=(
  build-essential ca-certificates curl wget git git-lfs jq ripgrep fd-find tree make
  pkg-config shellcheck smartmontools nvme-cli tmux
)
missing_packages=()

for package in "${required_packages[@]}"; do
  if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null \
    | grep -q "install ok installed"; then
    missing_packages+=("$package")
  fi
done

if ! command -v gh >/dev/null 2>&1; then
  missing_packages+=("gh")
fi

if ((${#missing_packages[@]})); then
  printf 'Missing Sprint 0 host tools:\n'
  printf '  %s\n' "${missing_packages[@]}"
  exit 1
fi

git --version
git lfs version
gh --version | head -n 1
jq --version
rg --version | head -n 1
fdfind --version
shellcheck --version | head -n 2
nvme --version
printf 'All Sprint 0 required host tools are installed.\n'
