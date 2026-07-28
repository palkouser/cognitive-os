# Provider configuration

Copy `config/providers.example.yaml` to the ignored `config/providers.local.yaml` and adjust
only non-secret settings. Every credential is named by the environment variable that carries
it; no credential value belongs in YAML. The default provider ID selects one explicit
registry entry — there is no automatic fallback and no adaptive routing.

Defaults across every adapter are: **disabled, offline, transient retention, read-only, zero
spend, live smoke off.** Turning any of them on is an operator decision, made in a file that
Git reviews.

## Selecting an adapter

Configuration version `2` dispatches on an explicit `adapter` discriminator:

| `adapter` | `kind` | What it is |
| --------- | ------ | ---------- |
| `minimax` | `network_api` | OpenAI-compatible chat completions |
| `openrouter` | `network_api` | OpenAI-compatible chat completions through the OpenRouter router |
| `claude_code` | `cli_agent` | local `claude --print`, read-only advisory |
| `codex_cli` | `cli_agent` | local `codex exec --json`, read-only advisory |

`kind` is kept for the provider taxonomy but is not what the loader dispatches on: Claude
Code and Codex are both `cli_agent`, so a `kind`-discriminated union could not tell them
apart. A version-1 document without an `adapter` is migrated on load for the two Sprint 21
adapters and refused for anything else, because guessing which CLI an entry meant is exactly
the guess that would silently start the wrong binary.

## Credentials

Read `docs/operations/provider-live-smokes.md` before enabling anything that authenticates.
In short:

* **OpenRouter** reads a key from `OPENROUTER_API_KEY`. Only that variable name is accepted —
  a configuration that pointed at a generic name could quietly harvest an unrelated key.
* **Claude Code and Codex** use the operator's own local subscription session. Cognitive OS
  never copies, exports, refreshes or manages those credentials, and there is no unattended
  service authentication for either.
* A CLI adapter's `environment_allowlist` is validated to exclude secret-like names, so a
  credential cannot be handed to a subprocess by widening the allowlist.

## Zero spend by default

OpenRouter ships with `require_free_model: true` and `maximum_spend_usd: 0.0`. Together they
refuse a paid model twice: once because the free-only policy rejects it, and once because
paid routing is refused while the maximum spend is zero. An unparsable price is treated as
**not free**, so a malformed catalog entry cannot buy its way past the policy.

`default_route: openrouter/free` is the router slug, not a model. OpenRouter resolves it
server-side and reports what it chose; that resolved identity is what the receipt records. A
*pinned* free slug is validated against the live catalog before use, because free
availability changes and a stale pin would fail as an upstream error rather than as the
typed unavailability it is.

## Data policy

`require_zero_data_retention: true` and `allow_data_collection: false` are the defaults, and
they are sent to OpenRouter as provider preferences on every request. Relaxing either is an
explicit operator decision recorded in the configuration file, and neither may be relaxed for
`internal` or `restricted` content.

## CLI safety flags

The two CLI adapters build their command line from validated configuration only — never from
a prompt, never from a path outside the fixture. The flags are asserted element by element in
`tests/cognitive_os/providers/claude_code` and `.../codex_cli`, because "the flags are
correct" is the claim a code review cannot check for a CLI it does not run.

* **Claude Code**: `--print --output-format json --json-schema … --permission-mode plan
  --allowed-tools Read,Glob,Grep --disallowed-tools Bash,Edit,Write,WebFetch,WebSearch
  --mcp-config '{"mcpServers":{}}' --strict-mcp-config --setting-sources "" --max-turns N
  --safe-mode`. Empty `--setting-sources` means no `CLAUDE.md`, no hooks, no plugins and no
  custom agents: that is customization this boundary does not grant. `--strict-mcp-config`
  with an empty MCP document means a user-level or project-level MCP file cannot add a server
  the adapter did not ask for. `--dangerously-skip-permissions` is never emitted.
* **Codex**: `exec -c approval_policy="never" -c mcp_servers={} -c tools.web_search=false
  --ephemeral --ignore-user-config --json --sandbox read-only --cd <workspace>
  --output-schema <path> --ignore-rules --skip-git-repo-check -`. codex-cli 0.144.6 has no
  `--ask-for-approval` flag, so the same policy is applied through the configuration path.
* A configured `FORBIDDEN_CLI_ARGUMENTS` list is refused at load, so a permissive flag cannot
  be reintroduced through configuration.

**Version compatibility.** Both adapters probe the installed binary for version and flag
acceptance before a live run and report `unavailable` rather than raising when the binary is
missing — a health check that raises cannot report "not installed". A CLI whose flags this
adapter has not reasoned about fails closed; it is never run with a reduced flag set.

## Retention, rights and sensitivity

A governed call declares an **intended use** before it happens, because the rights question
is not answerable in the abstract: the same response may be freely usable as transient advice
and prohibited as training input, and a decision made after the bytes exist is a decision
under pressure.

| Retention mode | What is kept |
| -------------- | ------------ |
| `none` (default) | nothing beyond the Event Store lifecycle |
| `hash_only` | the governance record and content hashes, never the text |
| `normalized_content` | additionally, the normalized response as an Artifact Store object |

`normalized_content` is granted only when **all** of these hold: usage rights are `verified`,
the secret scan `passed`, the sensitivity is `public` or `internal`, and no physical-deletion
obligation applies. Any one missing downgrades the call to `hash_only` — a recorded decision,
not a silent failure. The scan runs on the **unredacted** response, because scanning a
redacted value would always pass.

Rights are an operator input, never inferred: `unknown`, `prohibited` or `verified`, with an
evidence hash. A system that answered the rights question for itself would be marking its own
homework.

**Immutable-byte limitation.** The Artifact Store is content-addressed and immutable, so
bytes written under `normalized_content` cannot later be physically deleted. This is why a
directive combining `normalized_content` with `physical_deletion_required: true`, or with
`restricted` sensitivity, is **refused where it is written** rather than accepted and
downgraded later. If a deletion obligation may arise, use `hash_only` or `none`.

**Expiry** is an eligibility rule, not damage. An expired revision stays in the ledger as
correctly recorded history and simply stops being selectable; ledger health counts it and
stays green.

## Enabling and disabling

Every adapter can be enabled and disabled independently. A disabled provider is skipped by
the registry rather than registered-and-refused, and reports `unavailable` with a disabled
message in health output. Keep `config/providers.local.yaml` and every credential value
untracked.
