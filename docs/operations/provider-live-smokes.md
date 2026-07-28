# Provider live smokes

A live smoke calls a real provider. It is the only command in this repository that can spend
money or start a real agent, and everything below exists so that no single mistake is enough
to trigger one.

Live smokes are **excluded from normal CI**. Nothing in the credential-free lanes reads a
credential, opens a socket, or starts a provider binary.

## Authentication: what an operator does, and what this repository never does

| Provider | How it authenticates | What Cognitive OS does |
| -------- | -------------------- | ---------------------- |
| OpenRouter | `OPENROUTER_API_KEY` in the operator's environment | reads the named variable at call time; never logs, stores, echoes or forwards it |
| Claude Code | the operator's own local subscription session | starts `claude` as the operator, and nothing else |
| Codex | the operator's own local subscription session | starts `codex` as the operator, and nothing else |

**Subscription credentials are never copied, exported, refreshed, or managed by this
repository, and there is no unattended service authentication for either CLI.** A live smoke
is something a person runs at a terminal where they are already logged in. If a session has
expired, log in with the vendor's own tool; do not script a credential into the environment
to make an automated run possible.

Recovering a lost or leaked provider credential is **not** a Cognitive OS operation. It
requires separate operator authority through the provider's own console.

## The two-part opt-in

Both halves are required, and they are decided by different acts:

1. **Configuration.** `live_smoke_enabled: true` for that provider in
   `config/providers.local.yaml`, alongside `enabled: true`. This is an edit that Git
   reviews.
2. **The command line.** `--i-understand-this-calls-a-live-provider`, typed at the terminal.

Either alone does nothing and exits `4`. A single flag would make an accidental live call one
shell-history arrow-up away; a single configuration setting would make it invisible at the
call site.

## Preparing an isolated fixture root

A live CLI run executes inside its working directory, so that directory must not be anywhere
that matters. `live-smoke` refuses any isolation root that is the repository working tree, is
inside it, or contains it.

```bash
# 1. Copy the committed fixture somewhere outside the repository.
rm -rf /var/tmp/cogos-advisory-fixture
cp -r tests/fixtures/providers/advisory /var/tmp/cogos-advisory-fixture

# 2. Point the CLI adapter's working_directory at the copy's workspace.
#    config/providers.local.yaml:
#      working_directory: /var/tmp/cogos-advisory-fixture/workspace

# 3. Verify the copy hashes to its own manifest before anything runs.
uv run python scripts/provider.py fixture --fixture-root /var/tmp/cogos-advisory-fixture
```

The command re-hashes every file against the manifest and refuses a drifted, incomplete or
*unlisted-file* copy. An unlisted file would be readable by the provider, unscored and
unpinned, which is exactly how sensitive content would reach a fixture nobody re-hashed.

`live-smoke` additionally refuses to start if the configured `working_directory` is not the
verified fixture workspace.

## Running one

```bash
uv run python scripts/provider.py health \
  --config config/providers.local.yaml --provider openrouter \
  --allow-network --require-available

uv run python scripts/provider.py live-smoke \
  --config config/providers.local.yaml \
  --provider openrouter \
  --isolation-root /var/tmp/cogos-advisory-fixture \
  --i-understand-this-calls-a-live-provider
```

One call, under the configured caps. Retention defaults to `none`: a live smoke proves the
boundary works and is not an occasion to write a governance revision into the durable ledger.

## What the receipt contains, and what it never contains

Kept: provider and adapter identity, requested and resolved model, finish reason, request and
normalized-response hashes, retention mode, fixture ID and content hash, verifier verdict,
answer hash, token usage, elapsed time, and whether the workspace changed.

Never kept: the prompt, the response text, any credential, any login identity, any raw
provider payload, and any raw stderr. A hash is enough to prove two runs agreed; the prose is
not needed to prove anything and is a liability to store.

## How correctness is decided

By an independent deterministic verifier, not by the provider and not by the adapter that
parsed it. Schema validity proves shape — any provider can produce well-formed JSON. The
verifier requires one single finding that names the file, the function, the triggering input
and the resulting exception, and it refuses an answer that buries the right diagnosis in a
list of guesses.

A provider may not verify its own output: passing a verifier identity equal to the provider
ID is refused.

## Typed failures and safe rerun

| Failure | What it means | Safe rerun |
| ------- | ------------- | ---------- |
| `provider_model_unavailable` | the requested route or free model is not currently offered | yes, after re-checking the catalog with `health --allow-network` |
| `provider_budget_exceeded` | a paid model was refused under the free-only or zero-spend policy | do not rerun to force it; change the policy deliberately or pick a free model |
| `provider_authentication` / `provider_authorization` | the credential is missing, expired or not permitted | re-authenticate with the vendor's own tool, then rerun |
| `provider_timeout` / `provider_process` | the CLI exceeded its bounded timeout, or the process failed | yes; the process group is killed and the runner's temporary directory is removed either way |
| `provider_output_limit_exceeded` | the provider produced more output than the configured cap | yes, with a raised cap if the cap is genuinely too low — never with the cap removed |
| `provider_invalid_response` | the answer could not be normalized into the shared schema | yes; a malformed answer is a failed answer, not a reason to relax the parser |
| `provider_mutation_detected` | the advisory provider changed its working directory | **stop.** Investigate before rerunning; a read-only sandbox that wrote is a boundary failure, not a flake |
| `idempotency_key_reused` | a governance decision already exists for that model call ID under different content | do not retry with the same ID; a retry that reused it would overwrite a recorded decision |

Rerunning is always safe with respect to the ledger: re-recording *the same* execution finds
the first record and changes nothing. Re-*executing* under a reused model call ID is refused,
because it produces a second answer and would otherwise overwrite the first decision.

## After a run

The runner's temporary directory lives outside the workspace and is removed on every path,
including timeout and cap overflow. Verify the fixture tree is untouched:

```bash
uv run python scripts/provider.py fixture --fixture-root /var/tmp/cogos-advisory-fixture
```

A reported workspace change fails the smoke even when the answer was correct. Do not delete
the evidence stores to clear a failure.

## Two things that need separate operator authority

* **Artifact Store remediation.** The development Artifact Store pair carries a known
  metadata/bytes inconsistency inherited from Sprint 21C1. It is left untouched. Never make a
  verifier green by deleting orphan files or metadata; correcting it is a separate,
  explicitly authorised operation.
* **Provider credential recovery.** As above: the provider's own console, not this
  repository.
