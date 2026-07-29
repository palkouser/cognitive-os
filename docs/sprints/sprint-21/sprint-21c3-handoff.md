# Sprint 21C3 handoff — reality inputs

Sprint 21C1 built the durable evidence layer. Sprint 21C2 built the governed boundary
through which an outside teacher can reach it. Sprint 21C3 is where **real** outcomes
arrive — which is where the question stops being "can this be recorded safely" and becomes
"is any of it worth anything", a question nothing in 21C1 or 21C2 has answered.

## 1. Starting point

| | |
|---|---|
| Parent tag | `sprint-21c2-provider-baseline` — **not yet created**, see §6 |
| Parent branch | `feature/sprint-21c2-governed-providers` |
| Final implementation commit | `bc35ddd` |
| Parent final CI | 28 of 28 required checks green on `bc35ddd` |
| Parent migration head | `0015` |
| Next available migration | `0016` — only if Sprint 21C3 needs a schema change |
| Recommended branch | `feature/sprint-21c3-reality-inputs` |
| Gate C2 | **no-go** on condition 13 — see [gate-c2-assessment.md](gate-c2-assessment.md) |
| Gate L2 | **closed** |

**Read §6 before starting.** Gate C2 did not pass, and the release sequence that would
normally produce the parent tag has not run. Sprint 21C3 must not assume a
`sprint-21c2-provider-baseline` tag exists.

Verify the migration head is `0015` before writing anything.

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

## 4. Known failures and accepted limitations

| Limitation | Owner | Status |
|---|---|---|
| OpenRouter has no live-smoke evidence | operator | open; blocks Gate C2 condition 13 |
| Gate C2 condition 14 (merge, post-merge CI, tag) not attempted | operator | open; see §6 |
| Inconsistent development Artifact Store pair (`cognitive_os_dev` + `…/artifacts`): 4 rows without content, 5 orphan files | operator | untouched since Sprint 21C1; remediation proposed, needs separate authority |
| Required approving reviews disabled — one collaborator, no second eligible reviewer | operator | carried forward from C1 unchanged |
| No component is trained; none is active in any shipped configuration | — | by design |

The development pair's path-and-size fingerprint is `7e85d9a6…` over 5 files, unchanged
since Sprint 21C2 W0. Do not make a verifier green by deleting orphan files or metadata.

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

## 6. The release that has not happened

Gate C2 is a **no-go** on condition 13: two of the three required operator live smokes ran.
Because the gate did not pass, the release sequence in S21C2-078 — ready PR, protected
merge, exact-head post-merge `main` CI, annotated `sprint-21c2-provider-baseline` tag — was
not attempted.

The consequence for C3 is concrete: **there is no parent tag yet.** Two paths are open, and
both are operator decisions:

1. **Close condition 13 first.** Run the OpenRouter live smoke under the same bounds as the
   other two, re-assess, and then run the release sequence. C3 then starts from the tag as
   every previous sprint did.
2. **Release with the gap recorded.** Merge and tag with the annotation stating Gate C2 as a
   no-go on condition 13 and naming OpenRouter as the open item. C3 starts from that tag
   with an explicit inherited gap.

Do not start C3 by assuming the tag exists, and do not create it retroactively to make a
handoff table look complete. The work on the branch is complete and CI-verified at
`bc35ddd`; what is missing is evidence, and evidence is not something a tag can supply.
