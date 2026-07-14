#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker build --tag cognitive-os-sandbox:sprint-5 "$root/infra/sandbox"
