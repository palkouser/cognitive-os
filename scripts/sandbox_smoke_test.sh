#!/usr/bin/env bash
set -euo pipefail
image="${COGOS_SANDBOX_IMAGE:-cognitive-os-sandbox:sprint-5}"
output="$(docker run --rm --read-only --network none --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m "$image" id -u)"
if [[ "$output" == "0" ]]; then
  echo "Sandbox unexpectedly ran as root." >&2
  exit 1
fi
echo "Sandbox smoke test passed for non-root UID $output."
