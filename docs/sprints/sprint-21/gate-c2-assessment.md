# Gate C2 assessment — Governed Provider Boundary

- Sprint: 21C2
- Gate: C2 — Governed Provider Boundary
- Branch: `feature/sprint-21c2-governed-providers`
- Parent baseline: `aed2c1b0af280d3f0924a37eeddc191cd320e936` (tag `sprint-21c1-evidence-baseline`)
- Implementation pull request: [#214](https://github.com/palkouser/cognitive-os/pull/214)
- Migration head: `0015`
- Evidence:
  [`evidence/sprint-21c2-baseline.json`](evidence/sprint-21c2-baseline.json),
  [`evidence/sprint-21c2-provider-compatibility.json`](evidence/sprint-21c2-provider-compatibility.json),
  [`evidence/sprint-21c2-local-matrix.json`](evidence/sprint-21c2-local-matrix.json),
  [`evidence/sprint-21c2-live-smokes.json`](evidence/sprint-21c2-live-smokes.json)
- Decision: **conditional pass** — conditions 1–13 pass; condition 14 closes on release

## 1. Scope of this assessment

Gate C2 asks whether an operator can use OpenRouter, Claude Code and Codex as bounded
advisory teachers without losing the authority, provenance, retention and quarantine
guarantees Sprint 21C1 established. It does not ask whether any of them is *useful*.

§2.2 is explicit that any failed condition is a no-go and that a typed provider failure
does not substitute for the required live smokes. All three now have one, so condition 13
passes. Condition 14 is the release sequence and closes on the verified tag annotation, the
same way Gate C1 closed its final condition.

The live smokes are the reason this assessment is worth reading. Eight defects survived a
complete offline suite and were caught by calling the real providers (§3), two of them in
the data-policy path this sprint is built around.

**Gate L2 remains closed.** §5 states what that means.

## 2. Conditions

Each condition from §2.2 of the Sprint 21C2 backlog, with the evidence that decides it.

### 2.1 C1 parent tag, remote commit, final parent CI and migration head verified — **PASS**

`sprint-21c1-evidence-baseline` peels to `aed2c1b0af280d3f0924a37eeddc191cd320e936`, which
matches local `main`, remote `main`, and the head of the final parent CI run 30285564507
(`success`). The parent migration head was `0015`'s predecessor `0014`. All recorded in
`sprint-21c2-baseline.json` before any C2 work began.

The branch was cut from the peeled commit and carried four planning documents and no
source, schema or migration change.

### 2.2 Configuration selects every adapter unambiguously and rejects unsafe settings — **PASS**

Configuration version 2 dispatches on an explicit `adapter` discriminator. This is the one
place the design had to change rather than reuse: Claude Code and Codex are both
`cli_agent`, so a `kind`-discriminated union could not tell them apart, and the loader
would have had to guess which binary an entry meant. A version-1 document is migrated for
the two Sprint 21 adapters and refused for anything else — guessing is precisely what must
not happen when the guess starts a process.

Refusals are tested rather than documented: a secret-like name in an environment
allowlist, a shell fragment in an executable, a forbidden CLI argument, limits above the
hard maxima, an unknown adapter, and a `normalized_content` directive that no immutable
store could satisfy.

### 2.3 OpenRouter discovery, mapping, resolved-model capture, health, replay, typed failures — **PASS**

All offline, against a fake transport. Free-only routing, a paid refusal under both the
free-only policy and the zero-spend policy, an unknown model, an empty catalog, a
malformed catalog, and catalog staleness each produce their own typed outcome. An
unparsable price is treated as **not free**, so a malformed entry cannot buy its way past
the policy.

The router slug is passed through untouched and OpenRouter's resolved model is what the
receipt records. Twelve benchmark seed cases and four CI cases cover the routing matrix;
six more cover response normalization.

Two of the offline certainties turned out to be wrong when the API was actually called; see
§3.6 and §3.7.

### 2.4 Claude Code structurally enforces bounded read-only advisory operation — **PASS**

`--print --output-format json --json-schema … --permission-mode plan --allowed-tools
Read,Glob,Grep --disallowed-tools Bash,Edit,Write,WebFetch,WebSearch --mcp-config
'{"mcpServers":{}}' --strict-mcp-config --setting-sources "" --max-turns N --safe-mode`,
asserted element by element. `--dangerously-skip-permissions` is never emitted.

Empty `--setting-sources` means no `CLAUDE.md`, no hooks, no plugins, no custom agents.
`--strict-mcp-config` with an empty document means a user-level or project-level MCP file
cannot add a server the adapter did not ask for. Both were verified live against Claude
Code 2.1.219.

### 2.5 Codex structurally enforces ephemeral, read-only, no-approval operation — **PASS**

`exec -c approval_policy="never" -c mcp_servers={} -c tools.web_search=false --ephemeral
--ignore-user-config --json --sandbox read-only --cd <workspace> --output-schema <path>
--ignore-rules --skip-git-repo-check -`, asserted element by element. codex-cli 0.144.6
has no `--ask-for-approval` flag, so the same policy travels through the configuration
path; the compatibility probe records that, and the adapter verifies flag acceptance
before a live run.

Verified live against codex-cli 0.144.6.

### 2.6 The shared process boundary — **PASS**

One runner, shared by both CLI adapters, because two copies of process-group cleanup is two
places for an orphan to survive. It proves, under test:

- the prompt arrives on **stdin**, never in `argv` — where `/proc`, shell history and crash
  dumps would all see it. Sprint 21C1's adapter passed it positionally;
- the environment is built by **allowlist selection**, not denylist deletion, because a
  denylist has to anticipate every secret-carrying name and the one it misses is the leak;
- stdout and stderr byte caps terminate the process tree rather than growing a buffer;
- timeout, cancellation, cap overflow and a parser refusal all end in the same
  graceful-then-forced process-tree kill;
- content-based mutation detection, including the same-size edit a timestamp or length
  check would miss, and a symlink swap;
- runner-owned temporary files live **outside** the working directory and are removed on
  every path — an excluded path inside the fixture is a path a provider could change
  unobserved.

The cap handling was rewritten during W2: waiting on both readers with `gather` deadlocked
when a provider flooded stdout, and a cap overflow surfaced minutes later as a timeout.

### 2.7 Provider-output governance records the full decision — **PASS**

`provider_output_records` is append-only behind a `SECURITY DEFINER` controlled function;
`cogos_app` holds SELECT and EXECUTE only, verified by attempting a direct write. Each
immutable revision records rights decision and evidence hash, sensitivity, intended use,
retention mode, expiry, verifier status, identity and evidence hash, revision lineage, and
request/parameter/normalized-response content hashes.

Two implementations — in-memory and PostgreSQL — pass the same 27-case contract suite. The
in-memory reference deliberately keeps no current-state cache: it walks the appended
revisions the way the SQL walks its index, so agreement means something.

### 2.8 Governed intake only, quarantine, and no provider kind in `REAL_GOVERNED_SOURCE_KINDS` — **PASS**

The three provider source kinds belong to `VERIFIER_BACKED_SOURCE_KINDS` and are asserted
absent from `REAL_GOVERNED_SOURCE_KINDS` directly. Provenance is always
`OPERATOR_SUPPLIED`; attribution is `DIRECT` only when an independent verifier passed, and
`UNKNOWN` otherwise, which is what routes unverified output to quarantine.

Prohibited rights, a failed scan, an expired revision and a missing verifier are four
separate refusals on the way into intake, each tested.

### 2.9 No provider can approve, self-review, activate, or write active memory — **PASS**

There is no code path from the governed teacher to activation, approval or active memory,
and a test asserts the module imports nothing that could reach one. A provider that
supplies a verifier identity equal to its own provider ID is refused: schema validity
proves shape, not correctness.

### 2.10 No credential, identity, prompt or unredacted error is retained — **PASS**

Scanning runs on the **unredacted** response, because scanning a redacted value would
always pass. Receipts carry hashes, model identity, policy, usage, timing and status, and
a test asserts a verification carries no provider prose.

The one place this was nearly lost is worth naming: a non-zero CLI exit reported only
"non-zero status", and Claude Code writes its reason to stdout. The obvious fix — include a
stdout excerpt, as the runner already does for stderr — would have retained partial model
prose on every failure. Instead the runner takes an adapter-supplied diagnoser that returns
allowlisted scalar metadata only; the raw text never leaves the runner.

Two scanner findings were fixed at the source rather than silenced. `bandit` and
`detect-secrets` flagged an eligibility query comparing against `"passed"` beside a column
named `secret_scan_status`; the literals became enum values. A pragma there would have
trained the scanner to be ignored on the file that most needs it.

### 2.11 Migration `0015`, parity, grants, health, backup, restore, restart, downgrade/upgrade — **PASS**

Applied clean and incrementally, `0015 → 0014 → 0015`, with `alembic check` reporting no
drift on both sides. Backup and restore carry provider-output counts, a history hash and a
chain-continuity check, verified end to end on the isolated C2 pair. The restart smoke
re-reads every receipt in a new process after a container restart.

The controlled function's first version combined `max(revision)` with `FOR UPDATE`. It
migrated cleanly and would have failed on **every** runtime append — the same shape as the
`0014` defect. It is now an advisory transaction lock, which also serialises the race a row
lock cannot: two callers appending revision 1.

### 2.12 Normal CI covers all contracts and failure classes with no network, credential, CLI or GPU — **PASS**

28 checks green on `bc35ddd`. The provider lane installs no PostgreSQL extra, and when a
test needed SQLAlchemy it **moved lanes** rather than becoming a skip. The benchmark gate
is 35 CI cases and 77 seed cases at 100% expected-policy match, with zero network calls,
zero credential reads, zero subprocesses and zero cases labelled a real governed outcome.

CI also asserts the live command *refuses*: exit 4 without both opt-ins. Any other status
there would mean CI had just called a real provider.

Local matrix: 37 commands, every one at its expected exit status; 2023 passed, 12 skipped
across `tests/cognitive_os`, `tests/contract` and `tests/integration`. Every skip is an
absent optional extra or an explicitly opt-in live or Docker test.

### 2.13 One operator-approved live smoke per provider — **PASS**, with a reliability caveat

| Provider | Result |
| -------- | ------ |
| Claude Code 2.1.219 | **pass** — correct on every attempt |
| codex-cli 0.144.6 | **pass** — correct on every attempt |
| OpenRouter (`openrouter/free`) | **pass** — 5 correct in 22 attempts |

Every call ran against a verified copy of the public synthetic fixture outside the
repository, was scored by the independent verifier, left the workspace unchanged, wrote no
governance revision, and left no runner temporary directory behind. No prompt, response,
credential or identity is retained in the evidence.

**The OpenRouter number is reported as measured, not as achieved.** The router selects a
small free model, and most of them either diagnose the wrong thing or emit JSON that
violates the schema. Both outcomes are the boundary working: the independent verifier
scored the wrong answers wrong, and strict validation refused a malformed field
(`severityanas`) rather than coercing it. A single receipt is not evidence of reliability
and is not offered as any — the denominator is in the evidence file.

**Zero data retention was relaxed for OpenRouter, by explicit operator decision, for this
public fixture only.** No free OpenRouter endpoint offers ZDR; the strict default returns
`404 No endpoints found matching your data policy`. ADR 0087 permits a relaxed policy for
public content and forbids it for internal or restricted material, and the fixture is
public, synthetic and Apache-2.0. Data collection stayed denied, spend stayed at zero, and
the tracked example configuration keeps both strict defaults.

### 2.14 Protected merge, exact-head post-merge CI, annotated tag, remote verification — **OPEN**

The release sequence has not run. PR #214 has all 28 required checks green and
`enforce_admins` intact; no branch-protection control has been changed and no approval has
been fabricated. As in Gate C1, this condition closes on the verified tag annotation rather
than on a tracked document, so that the release does not need a second release commit to
describe itself.

## 3. What the live smokes found

The live smokes were the most productive hours of the sprint. Eight defects, every one
invisible to CI by construction:

1. **the advisory schema was rejected outright by Codex.** `advisory_schema_json()` emitted
   Pydantic's schema, which omits defaulted fields from `required`. `codex exec
   --output-schema` forwards it to a strict structured-output backend, which returned a 400
   naming the missing `evidence`. CI never sends the schema anywhere;
2. **the Codex prompt forbade the only capability Codex has.** The adapter reused the Claude
   Code advisory policy, which says "Do not run commands." Claude has native Read/Glob/Grep;
   Codex reads files *only* by running commands in its read-only sandbox. Codex correctly
   answered that it could not inspect the file. The boundary is `--sandbox read-only`, and a
   model instruction that fights the boundary is worse than none;
3. **the committed fixture task carried the same assumption** and is now provider-neutral;
4. **a non-zero CLI exit was undiagnosable** — see §2.10;
5. **`maximum_turns` defaulted to 3**, which an ordinary read-then-answer task exhausts, so a
   budget exhaustion read as a failure. Raised to 6; it is a cost bound, and the sandbox
   flags, timeout and output caps are unchanged;
6. **the live catalog carries `-1` prices** for models whose price is not fixed.
   `CatalogModel` constrains prices to `ge=0`, so the entire catalog failed to parse and the
   error escaped as a raw `ValidationError` rather than a typed provider failure. Normalising
   to infinity keeps the `ge=0` invariant true, so no later `price <= 0` test can read a
   variable price as a free one;
7. **the data policy never reached the wire.** `provider` is an OpenRouter extension, not a
   chat-completions parameter, and the OpenAI client validates its keyword arguments, so
   passing it at the top level raised `TypeError: unexpected keyword argument 'provider'`.
   Three tests asserted the policy was present by reading the payload dict the *fake* had
   accepted. This is the most uncomfortable finding in the sprint: the zero-data-retention
   setting the whole OpenRouter configuration is built around was being dropped before every
   request. There is now a test that reads the installed client's own signature;
8. **a network API was asked to read a file.** The live smoke handed all three providers the
   same task — "read the file in the directory you were given" — but OpenRouter has no
   filesystem, and a model asked to read a file it cannot see will confidently describe one
   it imagined. The first run diagnosed `calculate_mean` and `calculate_median`, neither of
   which exists. Workspace content is now inlined for non-CLI adapters, which stays
   deterministic because every byte is pinned by the fixture manifest.

Each has a regression test written against the shape the providers demand, so they hold
without a credential. That eight defects survived a full offline suite and were caught by
calling the real thing is the argument for condition 13, not against it.

## 4. Inherited and accepted limitations

**The inconsistent development Artifact Store pair is untouched.** `cognitive_os_dev` and
`/home/palkouser/projekt/cognitive-os-data/artifacts` still carry the Sprint 21C1
metadata/bytes mismatch: four rows whose content is missing, five orphan files. Sprint 21C2
created an isolated pair and wrote nothing to the development one. Its path-and-size
fingerprint still hashes to `7e85d9a6…` over 5 files, unchanged since W0. Remediation
remains proposed, not performed, and requires separate operator authority. No verifier in
this sprint was made green by deleting a file or a row.

**Required approving reviews remain disabled.** The repository has one collaborator and no
second eligible reviewer, so the C1 limitation is carried forward unchanged. No approval was
fabricated and no protection control was weakened to compensate.

**The OpenRouter free tier is unreliable for this task.** Five correct answers in 22
attempts. The failures are the boundary working — wrong diagnoses scored wrong, malformed
JSON refused — but an operator should not plan around a free model answering correctly, and
no learned pipeline should depend on one.

**Zero data retention cannot be satisfied on the free tier.** Relaxing it was an explicit
operator decision limited to the public synthetic fixture. Any use of OpenRouter for
internal or restricted content must keep `require_zero_data_retention: true` and accept
that this means paying for an endpoint that offers it.

## 5. Gate L2 status

> Governed provider evidence is available, but useful learned behaviour has not yet been
> demonstrated.

Nothing in this sprint measures accuracy, uplift, anti-forgetting or shadow performance. No
component is trained and none is active in any shipped configuration. Every benchmark case
measures whether a *policy* held — a refusal happened, a retention downgrade was recorded, a
mutation was caught — and passing all 112 of them says nothing about whether the system
learns.

Provider connectivity is not training, not useful improvement, and not activation
authorization.

## 6. Decision

**Gate C2: conditional pass.**

Conditions 1–13 pass on recorded evidence. Condition 14 — the protected merge, exact-head
post-merge CI, annotated tag and remote verification — is open and closes on the verified
tag annotation, as Gate C1's final condition did.

Two limitations travel with the pass and are not hidden by it: the OpenRouter free tier
answers this task correctly about one time in four, and zero data retention was relaxed for
the public fixture because no free endpoint offers it.
