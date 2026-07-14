#!/usr/bin/env bash
set -euo pipefail
docker image inspect "${COGOS_SANDBOX_IMAGE:-cognitive-os-sandbox:sprint-5}" \
  --format 'user={{.Config.User}} image={{.RepoTags}}'
