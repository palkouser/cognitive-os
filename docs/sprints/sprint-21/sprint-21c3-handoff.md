# Sprint 21C3 handoff — reality inputs

Sprint 21C1 built the durable evidence layer. Sprint 21C2 built the governed boundary
through which an outside teacher can reach it. Sprint 21C3 is where **real** outcomes
arrive — which is where the question stops being "can this be recorded safely" and becomes
"is any of it worth anything", a question nothing in 21C1 or 21C2 has answered.

## 1. Starting point

| | |
|---|---|
| Parent tag | `sprint-21c2-provider-baseline`, annotated tag object `23b3304890f4a90112514c633c7e2b768f7eeeff` |
| Parent commit | `94abe263c8f26f36c8f8c3bc7b86859c14c1f291`, equal to verified `main` and `origin/main` |
| Parent pull request | `#214`, merged |
| Parent final CI | run `30434494612`, 28 of 28 required checks green on the parent commit |
| Parent migration head | `0015` |
| Next available migration | `0016` — evidence-gated only; C3 requires no schema change by default |
| Recommended branch | `feature/sprint-21c3-reality-inputs` |
| Gate C2 | **pass** — all 14 conditions closed by the verified release annotation |
| Gate L2 | **closed** |

The remote tag and peeled commit were reverified on 2026-07-29. Reverify them and
migration head `0015` at sprint start because remote state can change.

The implementation authority is the
[Sprint 21C3 Technical Backlog](sprint-21c3-technical-backlog.md).

## 2. The APIs Sprint 21C3 inherits

### The provider boundary

`ModelProviderPort` is unchanged from earlier sprints. Four adapters now implement it, and
all four are constructed through exactly one place:

- `providers/factory.py` — `build_provider(config)`, a `match` over the `adapter`
  discriminator, and `build_registry(configuration)`. Deliberately not a plugin registry,
  entry-point scan or import-string constructor: each of those turns a configuration file
  into a mechanism for loading arbitrary code. A fifth adapter goes in the `match`.
- `providers/cli_process.py` — `BoundedCliRunner`, shared by both CLI adapters. Stdin
  prompt delivery, environment allowlisting, stdout/stderr byte caps, process-group
  termination, content-based mutation snapshots, runner-owned temporaries outside the
  working directory. A third CLI adapter uses this; it does not grow a second one.
- `providers/openrouter/` — catalog discovery, free-only routing, zero-spend policy,
  data-policy preferences, resolved-model capture.
- `providers/claude_code/`, `providers/codex_cli/` — read-only advisory adapters.
- `providers/openai_compatible.py` — the shared OpenAI-compatible mapping, extracted only
  once two adapters needed it.

`BoundedCliRunner` accepts an optional `diagnose_failure` callable. It receives the CLI's
stdout on a non-zero exit and must return **allowlisted scalar metadata only**. It exists
because Claude Code reports its failure reason on stdout, and it must never return a
message body: a failing advisory run can still hold partial model prose.

### Governance persistence

`ProviderOutputRepositoryPort` (`application/ports/provider_output.py`) — the only way to
touch provider-output governance. Two implementations pass one shared contract suite; a
third would have to pass it unchanged.

- `record_output`, `get_revision`, `get_latest`, `revision_history`
- `list_eligible(intended_use, moment, …)` — narrowing in SQL, final refusal by the
  contract's own `is_selectable_at`, so the two cannot disagree
- `resolve_source(provider_output_id, surface, moment) -> GovernedOutcomeReference`
- `count_revisions`

Every write goes through `cognitive_os.record_provider_output`. `cogos_app` holds SELECT
and EXECUTE only, so an application-role bug cannot rewrite a governance decision even if
it builds the SQL itself.

### Services

- `GovernedTeacherService.execute_with_receipt(request, directive, adapter_kind, rights,
  verifier, offer_to_intake)` — one provider call, one governance revision, one optional
  intake offer, in that order.
- `LearnedObservationIntake` — unchanged from 21C1, now aware of the three provider source
  kinds.
- `providers/advisory_fixture.py` — `load_advisory_fixture`, `verify_advisory_answer`. The
  independent verifier. It is not a provider and must never be given one.

### Health and operations

- `PostgresProviderOutputHealthService.check(provider_health=…, moment=…)`. Read-only.
  `integrity_failures` makes the ledger unhealthy; `provider_warnings` never does.
- `scripts/provider.py` — `list`, `health`, `replay`, `fixture`, `governance-verify`,
  `live-smoke`. Exit codes: 0 healthy, 1 failed, 2 usage, 3 not found, 4 policy refusal.

## 3. Invariants Sprint 21C3 must not break

**Retention is the directive intersected with the evidence.** `normalized_content` requires
verified rights, a passed secret scan, a `public` or `internal` sensitivity, and no
physical-deletion obligation. Any one missing downgrades to `hash_only` as a recorded
decision. A directive combining `normalized_content` with `restricted` sensitivity or a
deletion obligation is refused at construction, because the Artifact Store is immutable and
the obligation could never be met.

**Secret scanning runs on the unredacted value.** Scanning a redacted value always passes.
The order is scan, then decide, then retain.

**Rights are an operator input, never inferred.** `unknown`, `prohibited` or `verified`,
with an evidence hash. A system that answered the rights question for itself would be
marking its own homework.

**No provider source kind may enter `REAL_GOVERNED_SOURCE_KINDS`.** The three advisory
kinds belong to `VERIFIER_BACKED_SOURCE_KINDS`. Provenance is always `OPERATOR_SUPPLIED`;
attribution is `DIRECT` only when an independent verifier passed. A provider answering a
question is not a governed run, and a fixture that borrowed that label would become the
yardstick every later comparison is measured against.

**A provider may not verify its own output.** A verifier identity equal to the provider ID
is refused. Schema validity proves shape, not correctness.

**Re-executing under a reused model call ID is refused.** Re-recording the same execution
is a free no-op; re-executing produces a second answer and a second completed envelope, and
accepting it would let a caller with a reused ID overwrite a governance decision.

**Zero credentials, authorization headers, secret values, login identities, raw provider
bodies or raw stderr in logs, artifacts, events, reports, fixtures or Git.** Zero provider
calls or credential reads in normal CI.

**Live execution needs two independent opt-ins**: `live_smoke_enabled` in a reviewed
configuration file, and an explicit runtime flag. Do not collapse them into one.

**Open-development data does not require zero data retention.** Beginning with C3,
project-owned, generated, or rights-verified open-project material defaults to `public`,
`require_zero_data_retention=false`, and `allow_data_collection=true`. A live campaign
still needs the configuration and runtime opt-ins above, but it needs no separate ZDR
waiver or interactive retention prompt. Provider collection, storage, and sharing are
accepted for that material because iteration speed is the governing project priority.
This policy does not classify API keys, tokens, authorization material, subscription
identities, undisclosed personal data, or rights-restricted third-party material as
open-project data. Secret exclusion and source-rights evidence remain mandatory.

The decision is recorded as [ADR 0088](../../adr/0088-open-development-data-policy.md), which
amends the provider-side data expectations of
[ADR 0087](../../adr/0087-governed-provider-boundary-and-output-retention.md) and leaves its
authority table, retention modes, redaction order and secret-scan rules unchanged.

## 4. Known failures and accepted limitations

| Limitation | Owner | Status |
|---|---|---|
| OpenRouter free tier answered the C2 fixture correctly 5 of 22 times | — | measured; use for bounded diversity, never as C3 corpus coverage or correctness critical path |
| C2 limited its ZDR exception to the public fixture | operator | superseded for C3 and later work by the open-development data policy in §3 |
| Gate C2 release condition | operator | closed by protected merge, exact-head post-merge CI, and verified annotated tag |
| Inconsistent development Artifact Store pair (`cognitive_os_dev` + `…/artifacts`): 4 rows without content, 5 orphan files | operator | untouched since Sprint 21C1; remediation proposed, needs separate authority |
| Required approving reviews disabled — one collaborator, no second eligible reviewer | operator | accepted single-maintainer mode; retain 27 checks and `enforce_admins`, and reassess only if collaborator eligibility changes |
| No component is trained; none is active in any shipped configuration | — | by design |

The development pair's path-and-size fingerprint is `7e85d9a6…` over 5 files, unchanged
since Sprint 21C2 W0 and reverified at Sprint 21C3 W0. Do not make a verifier green by
deleting orphan files or metadata. The algorithm behind that value is now tracked as
`scripts/artifact_store_fingerprint.py`; until Sprint 21C3 it existed only in an operator's
shell history, so the claim could not be independently rechecked.

## 5. What Sprint 21C3 is for, and what it is not

C3 brings in **reality inputs**: real governed outcomes, the 200-outcome corpus, and the
executable corpus work. Those remain C3 scope and were deliberately not started here.

What C3 inherits is a boundary that can record an outside answer safely. What it does not
inherit is any evidence that an outside answer is *useful*. Every benchmark case in 21C2
measures whether a policy held; none measures accuracy, uplift, anti-forgetting or shadow
performance.

> Governed provider evidence is available, but useful learned behaviour has not yet been
> demonstrated.

Gate L2 stays closed until a sprint demonstrates useful learned behaviour on real governed
outcomes. Provider connectivity is not training, not useful improvement, and not activation
authorization. Do not carry a Gate L2 claim forward.

## 6. The release

Gate C2 is a **pass**. Pull request `#214` merged through the protected path, post-merge
`main` CI run `30434494612` completed with 28 of 28 required checks green, and annotated
tag `sprint-21c2-provider-baseline` peels to
`94abe263c8f26f36c8f8c3bc7b86859c14c1f291`, the same commit as verified `main` and
`origin/main`. The tag object is
`23b3304890f4a90112514c633c7e2b768f7eeeff`.

C3 must still revalidate those handles before branching. A future mismatch is release
drift to investigate, not permission to select another parent.
