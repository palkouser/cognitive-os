# Secret scan baseline

- Tool: detect-secrets 1.5.0
- Reviewed: 2026-07-14
- Scope: all repository files, including untracked Sprint 0 files; local environments,
  caches, Git metadata, and `.env.local` excluded
- Baseline: `.secrets.baseline`

The scan contains 31 unverified findings across 27 upstream files. Every finding is a
documented placeholder (`your_api_key`, local provider sentinel), or an explicit test
fixture (`test-key`, `provider-key`, `sk-test`). No verified credential, private key,
high-entropy token, or Cognitive OS local secret was found.

The additional `git grep` review found parameter names, environment lookups, placeholder
examples, and PDF-tool documentation examples only. `.env.local` is intentionally excluded
from Git and from the committed baseline; its values remain empty except for local paths.

Future commits are checked against `.secrets.baseline` by the pre-commit hook. New findings
must be reviewed and must not be added to the baseline merely to make the hook pass.
