# ADR 0087: The governed provider boundary and provider-output retention

- Status: Accepted
- Date: 2026-07-27
- Sprint: 21C2
- Stage gate: Gate C2 — Governed Provider Boundary
- Relates to: [ADR 0086](0086-learned-evidence-persistence-authority.md) (learned evidence
  persistence authority), [ADR 0081](0081-learning-substrate-extension-seam.md) (learning
  substrate seam)
- Amended by: [ADR 0088](0088-open-development-data-policy.md) — the provider-side
  zero-data-retention and data-collection expectations are superseded for open-development
  data from Sprint 21C3. The authority table, retention modes, redaction order and
  secret-scan rules below are unchanged.

## Context

Sprint 21C1 made learned evidence durable and proved that nothing can activate itself. It
contacted no provider. Sprint 21C2 opens exactly one door: an operator may use OpenRouter,
Claude Code and Codex as *advisory teachers*, and their output may reach the learning
plane's intake — quarantined, attributed, and never as a real governed run.

Three risks make this worth an ADR rather than three adapter pull requests.

1. **A teacher that can write is not advisory.** The Sprint 21C1 Claude Code adapter put
   the prompt in `argv`, compared `git status` strings to detect mutation, and had no hard
   byte cap on captured output. Each of those is the difference between "we asked a model
   for an opinion" and "we ran an agent with repository access".
2. **Provider bytes are not free to keep.** Retaining a provider response creates a usage
   rights question, a sensitivity question, a secret-scanning question and a deletion
   question, and the Artifact Store is content-addressed and immutable, so a retention
   policy that promises deletion is a promise the storage layer cannot keep.
3. **Provider availability reads as learning.** "We can call three models" is the kind of
   result that gets written up as progress on Gate L2. It is not. Gate L2 needs useful
   learned behaviour on real governed outcomes, and this sprint produces neither.

## Decision

### One authority per concern

| Information | Authority | Not the authority |
|---|---|---|
| Provider request lifecycle | the existing Event Store | the governance ledger or an adapter's return value |
| Normalized retained bytes | the existing content-addressed Artifact Store | the governance ledger, which stores hashes only |
| Rights, sensitivity, retention, verifier status, revision | `provider_output_records`, the new append-only governance ledger | the adapter, the provider, or the response payload |
| Learned observation classification | the C1 learned observation ledger, unchanged | the governance ledger |
| Quarantine review | C1 human-only review | any provider |
| Provider configuration | validated runtime configuration | environment defaults or adapter constructors |
| Current provider health | a read-only health service | any persistence layer |
| Active learned state | the C1 learned evidence service, unchanged | this sprint |
| Provider login and credential | the external CLI or provider credential store | Cognitive OS, ever |

The consequence that matters: **the governance ledger owns the decision, not the bytes and
not the classification.** It answers "may this output be retained, and may it be offered
for corpus or training use", and nothing else. Its answer is an input to C1 intake, which
still decides accept, quarantine or reject on its own terms.

### Providers are advisory and structurally powerless

An adapter may return structured content. It may not write active memory, activate,
approve, promote, roll back, review its own quarantine, mutate the working repository, or
classify its own output as a real governed run. The last one is enforced by an allowlist:
`openrouter_advisory`, `claude_code_advisory` and `codex_cli_advisory` are added to
`VERIFIER_BACKED_SOURCE_KINDS` and are *never* added to `REAL_GOVERNED_SOURCE_KINDS`, so a
provider claiming `REAL_GOVERNED_RUN` provenance is rejected by C1 intake as not credible.

A provider is also never its own verifier. Schema validity proves shape. The synthetic
fixture verifier is a separate deterministic function that knows the expected finding, and
its verdict — not the provider's confidence — is what reaches the governance record.

### One shared CLI process boundary, because there are two CLI adapters

`cognitive_os.providers.cli_process` is the single bounded runner for Claude Code and
Codex. It exists because two adapters need identical guarantees, not as a general process
framework:

- the prompt is delivered on stdin and never appears in `argv`;
- the executable, its fixed safety arguments, the working directory and the environment
  allowlist all come from validated configuration;
- the child runs in a new process group with no shell;
- stdout and stderr stream into hard-capped buffers, and exceeding a cap terminates the
  process tree rather than growing the buffer;
- timeout, cancellation, cap overflow and parser refusal all take the same termination
  path: graceful signal, bounded wait, forced process-tree kill;
- runner-owned temporary schema and configuration files are removed on every path.

Default limits are 120 s, 256 KiB stdout and 64 KiB stderr; hard maxima are 600 s, 1 MiB
and 256 KiB. Raising a hard maximum requires a new ADR revision and fresh
resource-exhaustion evidence, because "the output was truncated" is a recoverable failure
and "the runner consumed the host's memory" is not.

### Mutation is detected by content, not by `git status`

The C1 guard compared `git status --porcelain` before and after. That misses the case that
matters most: a file that was *already* dirty and was then modified again produces the same
status output. The C2 guard hashes relative path, entry type, executable mode and content
bytes for every file under the fixture root and compares complete snapshots, so
modification of a dirty file, creation, deletion, rename, symlink substitution and mode
change are all detected. Diagnostics carry paths and hashes only — never file content.

Live CLI smokes run against a copy of a committed public synthetic fixture in a temporary
directory. The Cognitive OS worktree is never a provider working directory.

### OpenRouter reuses the installed OpenAI client

OpenRouter is OpenAI-API-compatible, `openai` is already a declared dependency, and the
MiniMax adapter already proves the request and response mapping against that client. Adding
LiteLLM or an OpenRouter SDK would add a dependency, a second retry policy and a second
error taxonomy to reach a boundary the repository already has. What stays
OpenRouter-specific is what is genuinely specific: the base URL, the model catalog, routing
metadata, the data-collection and zero-data-retention preferences, and the error bodies.

Free model availability is dynamic. `openrouter/free` is the default route, a pinned free
model is validated at runtime before use, and the disappearance of a previously observed
model is a typed `MODEL_UNAVAILABLE` outcome — not a code defect, and not a reason to pin a
slug as permanently available.

### `codex exec` has no `--ask-for-approval`, so the config override is used

Verified against codex-cli 0.144.6: `--ask-for-approval` is a top-level flag that
`codex exec` rejects. The adapter therefore emits `-c approval_policy="never"`, which is the
same policy through the documented configuration path and is not a weaker setting: `exec` is
non-interactive, and the sandbox remains `read-only` regardless. Every emitted flag is parse-
probed against the installed binary before execution, and an unsupported required flag makes
the adapter typed-unhealthy instead of silently dropping it. The probe results are recorded
in `docs/sprints/sprint-21/evidence/sprint-21c2-provider-compatibility.json`.

### A separate governance ledger, because C1 hashes are immutable

`LearnedObservationRecord` is hash-bound and already has rows under migration `0014`.
Adding optional retention fields to it would change the canonical hash of every existing
record, which is precisely the drift the C1 hashing exists to detect. Retention therefore
lives in a new versioned contract, `ProviderOutputRecord`, in a new append-only table
`provider_output_records` created by migration `0015`.

The ledger is append-only with `(provider_output_id, revision)` uniqueness. A rights
revocation, sensitivity correction, verifier correction or expiry change is a *new
revision*; previous rows stay immutable and auditable. There is no materialized
current-state table: the latest revision is the maximum valid revision for one stable
output ID, served by a bounded index. A projection would be a second authority and the C1
replay machinery already shows what maintaining one costs.

### Retention defaults to keeping nothing

Three modes, and `none` is the default:

| Mode | What persists |
|---|---|
| `none` | nothing: no governance record, no request or response artifact |
| `hash_only` | governance metadata and hashes; no provider content bytes |
| `normalized_content` | the validated normalized response only; never the raw provider payload |

`normalized_content` requires all of: verified usage rights for the declared intended use,
a passed secret scan, a sensitivity the policy permits for storage, no physical-deletion
obligation, and a retained artifact whose hash matches the governance record. Any of those
missing fails closed.

`expires_at` controls *eligibility for future use*. It does not claim that bytes were
deleted. If a retention obligation genuinely requires physical deletion, the correct C2
answer is `hash_only` or `none`, because the Artifact Store is immutable and content-
addressed and this sprint does not implement garbage collection. Promising deletion the
storage layer cannot perform would be worse than declining to retain.

### Redaction happens before persistence, not after

Authorization headers, bearer tokens, URL credentials, common API-key shapes, environment
secret values and login identities are redacted before logging, before error normalization,
before event creation and before artifact creation. Secret *scanning* is separate and
tri-state — not run, passed, failed — because "we redacted it" and "we checked and found
nothing" are different claims, and a failed scan must block `normalized_content` retention
even though redaction would have masked the value. The record stores the scan's rule-set
version and an evidence hash, never the matched text.

## Alternatives considered

- **Extend `LearnedObservationRecord` with retention fields.** Rejected: it changes the
  canonical hash of existing `0014` rows.
- **A materialized `provider_output_current` table.** Rejected: a second authority whose
  drift would need its own replay and health checks, for a query an index already answers.
- **A generic provider plugin framework.** Rejected: the sprint adds two adapters. The
  existing registry plus one explicit `match` in a small factory is sufficient, and dynamic
  import-string construction would let configuration widen authority.
- **One process runner per CLI adapter.** Rejected: two copies of process-group cleanup is
  two places for an orphan process to survive.
- **Reusing `MemorySensitivity` wholesale.** Partly adopted: the enum is reused, but
  `CONFIDENTIAL` is refused, because C1 intake's `KNOWN_SENSITIVITIES` does not recognise it
  and an unrecognised label reaching intake would quarantine every governed output.
- **Retaining raw provider payloads for debugging.** Rejected: the raw body is exactly the
  surface that carries provider request IDs, routing metadata and unredacted error text.

## Consequences

Positive:

- an operator can use three teachers through one normalized contract, with one retry
  policy, one error taxonomy, one event lineage and one retention decision path;
- the default execution retains nothing, so the safe path is also the lazy path;
- every trust boundary has a testable consequence: `argv` contents, snapshot equality,
  process-tree emptiness, capped byte counts, allowlist membership, hash equality;
- normal CI never needs a credential, a network, an installed CLI or a GPU.

Negative, and accepted:

- three adapters and a governance ledger are more surface than Sprint 21C1 shipped;
- `expires_at` is an eligibility rule, not a deletion guarantee, and the documentation has
  to say so every time it is mentioned;
- a provider output can never be a real governed run in C2, so the C3 corpus target cannot
  be met by calling providers more often;
- an unsupported CLI flag makes an adapter unhealthy rather than degrading it, which will
  break advisory execution on a CLI upgrade until the manifest and tests are updated. That
  is the intended failure direction.

## Verification

- `argv` assertions on fake executables for both CLI adapters, plus a test that the prompt
  string never appears in any recorded argument;
- content-and-mode snapshot fixtures covering write, create, delete, rename, symlink, mode
  change and *modification of an already dirty file*;
- process-tree emptiness after timeout, cancellation, stdout cap, stderr cap and parser
  refusal, including grandchild processes;
- adversarial redaction fixtures with seeded secrets in nested payloads, split fields,
  stderr and provider error bodies, asserted against every persisted surface;
- direct invocation of the `0015` controlled function with UUID, integer, boolean,
  timestamp, enum, JSON and nullable fields — applying the migration is not evidence that
  the function works, which is the exact defect `0014` shipped with;
- one shared repository contract suite run unchanged against the in-memory and PostgreSQL
  provider-output stores;
- an offline benchmark of at least 24 CI and 72 fixed-seed policy cases at 100% expected-
  policy match;
- one operator-approved bounded live smoke per provider, each independently verified,
  each leaving its fixture byte-for-byte unchanged.

## References

- Sprint 21C2 technical backlog: `docs/sprints/sprint-21/sprint-21c2-technical-backlog.md`
- Provider compatibility manifest:
  `docs/sprints/sprint-21/evidence/sprint-21c2-provider-compatibility.json`
- OpenRouter quick start, free router, model discovery, error reference, zero-data-retention
  and data-collection policy documentation
- Codex `exec` command and sandbox configuration reference (codex-cli 0.144.6)
- Claude Code CLI usage and permission-mode reference (Claude Code 2.1.219)
