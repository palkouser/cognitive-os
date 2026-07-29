# Claude Code advisory operation

Claude Code runs as a bounded, read-only advisory teacher. It is non-interactive, limited by
timeout, output cap and maximum turns, and returns the one Cognitive OS-owned advisory schema
that all three providers answer in: summary, findings, recommendations, risks and
verification steps.

The exact command line, the empty MCP configuration and the disabled setting sources are
documented in [provider-configuration.md](provider-configuration.md#cli-safety-flags).
`--dangerously-skip-permissions` is never emitted.

## Running one

There is one live path, and it is the operator CLI:

```bash
uv run python scripts/provider.py live-smoke \
  --config config/providers.local.yaml \
  --provider claude-code \
  --isolation-root /var/tmp/cogos-advisory-fixture \
  --i-understand-this-calls-a-live-provider
```

Read [provider-live-smokes.md](provider-live-smokes.md) first: it covers the two-part opt-in,
how to build and verify an isolated fixture root, what the receipt keeps, and what to do with
each typed failure.

Claude Code never runs against the Cognitive OS worktree. It runs against a verified copy of
the public synthetic advisory fixture, made outside the repository, and the smoke fails if a
single byte of that copy changed — a correct diagnosis from a provider that edited its
workspace is still a failure.

## Standing limits on advisory output

Advisory output is untrusted review context. It cannot write active memory; activate,
approve, promote or roll back a learned component; review its own quarantined output; be
classified as a real governed run; call a workspace mutation tool; approve a patch; satisfy
an acceptance criterion; override a verifier result; or be the only evidence for a decision.

Whether an answer is *correct* is decided by an independent deterministic verifier, never by
Claude Code and never by the adapter that parsed its output.
