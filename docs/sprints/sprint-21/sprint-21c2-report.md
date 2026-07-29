# Sprint 21C2 report — Governed Teacher and Provider Boundary

- Sprint: 21C2
- Stage gate: C2 — Governed Provider Boundary
- Gate C2 decision: **conditional pass** — see
  [gate-c2-assessment.md](gate-c2-assessment.md)
- Gate L2: **closed**

> Governed provider evidence is available, but useful learned behaviour has not yet been
> demonstrated.

## 1. Source state

| | |
|---|---|
| Required parent commit | `aed2c1b0af280d3f0924a37eeddc191cd320e936` |
| Parent tag | `sprint-21c1-evidence-baseline` |
| Parent migration head | `0014` |
| Branch | `feature/sprint-21c2-governed-providers` |
| Implementation pull request | [#214](https://github.com/palkouser/cognitive-os/pull/214) |
| Final implementation commit | `bc35ddd` |
| Final migration head | `0015` |
| Diff against parent | 110 files, +19108 / −1679 |

The parent baseline was verified before any work started: `main`, `origin/main`, and the
local and remote peeled tag all resolved to `aed2c1b0…`, CI run `30285564507` succeeded on
that same commit, and the migration head was `0014`. The branch was cut from the explicit
SHA and carried four planning documents — no source, schema or migration change.

## 2. Delivered work

| Backlog ID | Delivered |
|---|---|
| S21C2-000..002 | Control checks, verified baseline, isolated C2 database and artifact pair, read-only fingerprint of the inconsistent development pair |
| S21C2-003 | ADR 0087 — governed provider boundary and output retention |
| S21C2-010..012 | Configuration version 2 with an explicit `adapter` discriminator, `ProviderOutputRecord` and retention contracts, exported schemas, narrow ports |
| S21C2-013 | `provider_output_records`, migration `0015`, append-only trigger and controlled write function |
| S21C2-020..022 | One bounded CLI process boundary, content-based mutation guard, redaction and tri-state secret scanning |
| S21C2-023..024 | One construction boundary (`build_provider`), unified typed health |
| S21C2-030..033 | OpenRouter adapter: catalog discovery, free-only routing, zero-spend policy, data-policy preferences, resolved-model capture |
| S21C2-040..043 | Claude Code hardened behind the shared runner: stdin prompt, empty MCP, no setting sources, bounded turns |
| S21C2-050..053 | Codex adapter: ephemeral read-only `exec --json`, allowlisted event types, fail-closed JSONL parsing |
| S21C2-060..065 | In-memory and PostgreSQL governance repositories on one contract suite, `GovernedTeacherService`, learned-intake integration, health, backup, restore |
| S21C2-070..072 | Unified operator CLI, public synthetic advisory fixture and independent verifier, 35-case CI and 77-case seed benchmark |
| S21C2-073 | Draft PR opened in W1; CI exercised the controlled function, not only migration application |
| S21C2-074 | Complete local verification matrix, 37 commands |
| S21C2-075 | Three operator-approved live smokes: Claude Code, Codex and OpenRouter each produced a verified-correct answer |
| S21C2-076 | Provider configuration, live-smoke, Claude Code and Codex operator runbooks |
| S21C2-077..079 | Gate C2 assessment, this report, Sprint 21C3 handoff |

## 3. What the sprint actually decided

Four decisions were forced by evidence rather than chosen up front, and each is where a
plausible alternative would have been wrong.

**The configuration discriminator had to be explicit.** Claude Code and Codex are both
`cli_agent`. A `kind`-discriminated union could not tell them apart, so the loader would
have had to guess which binary an entry meant — and the guess starts a process. Version 2
adds an explicit `adapter`, migrates version-1 documents for the two known adapters, and
refuses to infer anything else.

**Retention is the directive intersected with the evidence, never the directive alone.**
`normalized_content` needs verified rights, a passed scan, a storable sensitivity and no
deletion obligation. Any one missing downgrades to `hash_only` as a *recorded* decision.
Separately, a directive that no immutable store could ever satisfy — `normalized_content`
with `restricted` sensitivity or a physical-deletion obligation — is refused where it is
written rather than accepted and quietly downgraded later, so the caller says `hash_only`
out loud instead of discovering it in a receipt.

**"Retries cannot duplicate provider-output records" is two different claims.** Writing the
test made that visible. Re-recording the *same* execution finds the first record and
changes nothing: that is the real retry, where persistence failed and the same answer goes
again. Re-*executing* under a reused model call ID produces a second answer and a second
completed envelope, so the content differs — and that is now refused, because silently
taking it would let a caller with a reused ID overwrite a governance decision. The first
version of the code conflated them and the test rightly failed.

**Schema validity is not correctness, so the verifier lives outside the provider.** Any
provider can emit well-formed JSON. The independent verifier requires one finding naming
the file, the function, the triggering input and the exception, refuses concepts spread
across several findings, and caps the finding count — a shotgun is not a diagnosis. A
provider supplying its own verifier identity is refused outright.

## 4. Defects found and fixed

**Two would have failed at runtime after migrating cleanly.** The controlled function in
`0015` first combined `max(revision)` with `FOR UPDATE`, which PostgreSQL rejects; the
migration applied fine and every append would have failed — the same shape as the `0014`
defect. It is now an advisory transaction lock, which additionally serialises the race a
row lock cannot: two callers appending revision 1. The bounded runner waited on both output
readers with `gather`, so a provider flooding stdout deadlocked and a cap overflow surfaced
minutes later as a timeout.

**One was of my own making, in the exact shape C1 had already caught.** A W1 test wrote
artifact bytes to a pytest temporary directory while the metadata went to the shared CI
database, recreating the metadata-without-bytes drift that restore verification exists to
find. Restore verification found it.

**Eight came from the live smokes and none was reachable from CI.** The advisory schema
omitted defaulted fields from `required`, which Codex's strict structured-output backend
rejected with a 400. The Codex adapter reused Claude Code's policy text forbidding
commands, which is the only way Codex can read a file — the prompt made the task
impossible, and Codex said so. The committed fixture task carried the same assumption. A
non-zero CLI exit reported only "non-zero status" because Claude Code writes its reason to
stdout. `maximum_turns` defaulted to 3, which an ordinary read-then-answer task exhausts.
The live catalog carries `-1` prices, which the contract rejected outright. The live smoke
asked a network API to read a file it has no filesystem for, and got a confident
description of functions that do not exist.

**The eighth is the one worth dwelling on.** OpenRouter's `provider` preferences were passed
as a top-level keyword argument, which the OpenAI client rejects — so the zero-data-retention
and data-collection policy this sprint is built around was being dropped before every single
request. Three tests asserted the policy was present; all three read the payload dict the
*fake transport* had accepted. A fake built from what the adapter expects cannot catch what
the real client refuses. There is now a test that reads the installed client's own
signature. Details in §3 of the gate assessment.

The tempting fix for the undiagnosable exit — copy a stdout excerpt into the error, as the runner
already does for stderr — would have retained partial model prose on every failure. The
runner now takes an adapter-supplied diagnoser returning allowlisted scalar metadata only,
and the raw text never leaves the runner.

**Two scanner findings were fixed at the source rather than silenced.** `bandit` flagged a
ruleset-version constant and an eligibility query comparing against `"passed"` beside a
column named `secret_scan_status`. Both became references to the real constants. A pragma
would have trained the scanner to be ignored on the files that most need it.

## 5. Evidence

| Check | Result |
|---|---|
| CI on `bc35ddd` | 28 of 28 required checks green |
| Local matrix | 37 commands, all at expected exit status |
| Full repository suite | 2023 passed, 12 skipped |
| Provider boundary benchmark | 35 CI + 77 seed cases, 100% expected-policy match |
| Live smokes | 3 of 3 providers produced a verified-correct answer |
| Migration | `0015` clean, incremental, `0015 → 0014 → 0015`, no drift |
| Backup / restore / restart | pass on the isolated C2 pair |
| Security | bandit 0 findings, detect-secrets clean, pip-audit clean |

All 12 skips are absent optional extras or explicitly opt-in live and Docker tests. Two are
the live CLI advisory tests, which are opt-in by design. No provider behaviour is hidden by
a skip.

The benchmark measures whether a policy held — a refusal happened, a retention downgrade
was recorded, a mutation was caught. It measures nothing about usefulness.

## 6. Limitations carried forward

**The inconsistent development Artifact Store pair is untouched.** Its path-and-size
fingerprint still hashes to `7e85d9a6…` over 5 files, unchanged since W0, and zero C2
writes reached it. Remediation remains proposed and needs separate operator authority. No
verifier was made green by deleting a file or a row.

**Required approving reviews remain disabled.** One collaborator, no second eligible
reviewer; the C1 limitation is carried forward unchanged. No approval was fabricated and no
protection control was weakened.

**The OpenRouter free tier is unreliable for this task**: 5 correct in 22 attempts. The
failures are the boundary working — wrong diagnoses scored wrong by the independent
verifier, malformed JSON refused by strict validation — but nothing should be planned around
a free model answering correctly.

**Zero data retention was relaxed for OpenRouter**, by explicit operator decision, for the
public synthetic fixture only. No free endpoint offers ZDR. Internal or restricted content
must keep the strict default and accept that this means paying for an endpoint that honours
it. The tracked example configuration is unchanged.

## 7. Gate status

**Gate C2: conditional pass.** Conditions 1–13 pass on recorded evidence; condition 14 — the
protected merge, exact-head post-merge CI and annotated tag — is open and closes on the
verified tag annotation, as Gate C1's final condition did.

**Gate L2: closed.** No component is trained and none is active in any shipped
configuration. Provider connectivity is not training, not useful improvement, not
anti-forgetting evidence, and not activation authorization.
