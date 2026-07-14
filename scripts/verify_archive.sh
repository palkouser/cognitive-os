#!/usr/bin/env bash
set -euo pipefail

archive="${COGOS_ARCHIVE:-/home/palkouser/backup/cognitive-os-archive}"
test_file="$archive/.write-test-$$"
trap 'rm -f "$test_file"' EXIT

findmnt /home/palkouser/backup
df -hT /home/palkouser/backup
test -d "$archive/source-snapshots"
printf 'Cognitive OS archive test\n' >"$test_file"
grep -Fx 'Cognitive OS archive test' "$test_file"
printf 'Archive read/write verification passed: %s\n' "$archive"
