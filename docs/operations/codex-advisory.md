# Codex advisory operation

Codex runs as a bounded, read-only advisory teacher through `codex exec --json`, answering
the same Cognitive OS-owned advisory schema as the other two providers so that one
deterministic verifier can score any of them.

The exact command line — `--sandbox read-only`, `--ephemeral`, `--ignore-user-config`,
`--ignore-rules`, an empty `mcp_servers`, disabled web search, and `approval_policy="never"`
applied through the configuration path because codex-cli 0.144.6 has no `--ask-for-approval`
flag — is documented in
[provider-configuration.md](provider-configuration.md#cli-safety-flags).

## Running one

```bash
uv run python scripts/provider.py live-smoke \
  --config config/providers.local.yaml \
  --provider codex-cli \
  --isolation-root /var/tmp/cogos-advisory-fixture \
  --i-understand-this-calls-a-live-provider
```

Read [provider-live-smokes.md](provider-live-smokes.md) first: it covers the two-part opt-in,
the isolated fixture root, what the receipt keeps, and what to do with each typed failure.

## Reading the JSONL stream

Codex streams events and the last authoritative one carries the final message. Three rules
make that safe to consume, and all three are refusals rather than best-effort parsing:

* a **truncated or malformed** JSONL line is a refusal, because a trailing partial line is
  what truncation at the stdout cap looks like and accepting it would turn a capped run into
  a short answer;
* an **unrecognised event type** is a refusal. A future Codex version adding an event this
  adapter has not reasoned about may be the one carrying the real answer, and picking the
  previous message would be a plausible-looking wrong result;
* a **missing final message**, and a final message that does not match the advisory schema,
  are two further distinct refusals.

Narration events the adapter has deliberately chosen to ignore are listed explicitly, so
"we chose to ignore this" and "we did not recognise this" stay different claims.

## Standing limits on advisory output

Identical to Claude Code: advisory output is untrusted review context. It cannot write active
memory; activate, approve, promote or roll back a learned component; review its own
quarantined output; be classified as a real governed run; call a workspace mutation tool;
approve a patch; satisfy an acceptance criterion; override a verifier result; or be the only
evidence for a decision.
