#!/usr/bin/env bash
set -euo pipefail

if git ls-files | grep -E '(^|/)README\.(hu|zh|ja|ko|ru|es|fr|de|pt|it|tr|ar)(-[A-Z]+)?\.md$'; then
  echo "Translated README files are not allowed."
  exit 1
fi

if rg -n \
  --hidden \
  --glob '!.git/**' \
  --glob '!uv.lock' \
  --glob '!LightAgent/**' \
  --glob '!scripts/check_repository_language.sh' \
  --glob '!docs/baseline/generated/**' \
  '(kérem|feladat|fejlesztés|környezet|működik|hiba|magyar|projekt célja)' \
  .; then
  echo "Potential non-English Cognitive OS content found."
  exit 1
fi

echo "Repository language check passed."
