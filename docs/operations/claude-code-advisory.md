# Claude Code advisory operation

Claude Code must be locally installed and authenticated before an opt-in smoke test. Advisory
mode is non-interactive, read-only, limited by timeout and maximum turns, and returns the
Cognitive OS-owned advisory schema: summary, findings, recommendations, risks, and
verification steps.

Run only with explicit opt-in:

```bash
COGOS_RUN_CLAUDE_CODE_LIVE=1 \
uv run python scripts/claude_code_advisory_smoke_test.py \
  --working-directory /home/palkouser/projekt/cognitive-os
git status --short
```

The runner never uses `--dangerously-skip-permissions`. A repository status change is a
policy violation; inspect it manually because the adapter does not delete user files.
