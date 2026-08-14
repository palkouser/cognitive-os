# Sprint 22C Execution Log

Continual learning, knowledge acquisition, and the campaign pipeline. Executed against the
[Sprint 22C Technical Backlog](sprint-22c-technical-backlog.md), whose §0 incorporates the
[Sprint 21D4](../sprint-21/sprint-21d4-technical-backlog.md) execution contract unchanged.

Waves are recorded newest first.

---

## W0 outcome — the authority, the gate that blocks, the drivers, and the freezes

Five scripts, one new contract module, six sealed records, two test modules with **54
tests**, **six findings**, one decision and one carried observation.

22B's W0 had five thresholds in front of it and asked the gate owner for nothing. 22C's has
five *sentences* in front of it — four pipeline-integrity claims and one usefulness claim
nothing in the programme has ever made — and it does have to ask the gate owner for
something, because §1.3 puts a rights gate in front of the whole sprint and the review has
not concluded. So this wave splits cleanly in two: **everything that does not need the real
source is finished**, and **the one thing that does is surfaced as a blocking dependency
with the gate built, executed, and currently refusing.**

Three of the six findings were found only by *running* the pipeline rather than reading it,
and the sharpest of them — W0-F3 — is the exact failure §3.1 predicted at the corpus →
semantic → memory seam, at fixture scale, in W0, for the price of one afternoon rather than
of cycle 2.

### S22C-000 and S22C-001 — the starting point, read from the authority that owns it

[`sprint-22c-baseline.json`](evidence/sprint-22c-baseline.json), integrity
`6ddd1e8950d7a923…`, file `578a36f2ae88c035…`.

| Fact | Result |
|---|---|
| `sprint-22b-scale-baseline` resolves remotely as an annotated tag | yes, object `084d561ddc3def7a…` peeling to `dc4006116ff2cfac…` |
| local and remote tag handles agree | yes |
| **the tag peels to the current `origin/main`** | yes — checked rather than assumed, because 22B had to re-cut this tag after a squash merge stranded it |
| both 22C outcome tags | **absent**, checked rather than assumed |
| 22B exact-head post-merge CI run `31804585618` | re-read from the API, **30 of 30 successful** |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015`, counted from `infra/postgres/alembic/versions` |
| **fourteen** predecessor artifact roots | fingerprinted through the released `reality_integrity.fingerprint`; the twelve with a released expectation match it, drift **zero** |
| 22B's own two roots | **first observations**, for exactly the reason 22A's own root was one in 22B |
| stores written to before this record | **none** |

The record also binds, **by hash rather than by retyped number**, the two reproductions W1
is required to beat. That is the whole point of the file for this sprint. W1 owes
`items_missing_an_event == 0` after re-running 22B's crash, and clustered recall back over
`0.95` from the sealed `0.9410`; a baseline that restated those as constants would let the
comparison drift the moment either record moved. The three sealed throughput numbers 22B
measured are bound the same way, as campaign budget lines a later wave reads rather than
rediscovers.

**S22C-001**: four databases were created through the released
`postgres_provision_evidence.sh` under the `cognitive_os_s22c` prefix — the campaign store,
a **holdout store**, an integration store, and a restore target for W1's W4-F1 repair. All
four migrated to head `0015`, fifteen migrations, 114 tables, and the app role has **no
DELETE** on `cognitive_os.events`, inherited from the released grants rather than applied by
hand. Roots `artifacts-s22c`, `backups-s22c` and `artifacts-s22c-holdout` created empty.
The baseline was taken *before* any of this, so its `before` is genuinely before.

The holdout store exists because §2.2c requires the holdout to live outside the campaign
store and 22B's W1-F6 is a standing rule here: separate **by construction, not by promise**.
Its name is not derivable from the campaign's own connection string, so a driver handed only
`COGOS_DATABASE_URL` cannot reach it by any code path.

### S22C-002 — the rights gate, and the one thing this wave asks for

[`sprint-22c-rights-gate.json`](evidence/sprint-22c-rights-gate.json), integrity
`85e0b74a865b0da5…`.

The allocation's §7 permitted the source-rights review to begin during the scale sprint.
Read from the repository rather than from the plan's expectation: **it has not concluded.**
22B's execution record names no rights work, and no rights evidence file exists. §3.2 says
exactly what W0 does with that, and this wave did it — surfaced the blocking dependency with
a named owner and the exact list of fields a concluded review must produce, and **registered
no substitute source and picked no chapter**, because §1.3 reserves that choice to the gate
owner and a campaign run on an unclear source is evidence that cannot be released.

What the wave refused to do is more interesting than what it recorded, so the gate is
**executed** rather than described. Five probes, four of which must refuse:

| Probe | Result |
|---|---|
| no rights record at all | refused |
| **a clearance issued against different bytes** | refused — the dangerous one, because it looks cleared |
| a record carrying an unconcluded review | refused by the contract itself: `CampaignSourceRights` cannot hold `status=not_cleared` |
| a campaign use the clearance does not permit | refused by `CampaignManifestV1` |
| a matching clearance for the fixture chapter | **admitted, as it must be** |

The fifth probe is the one that makes the other four mean something. A gate that refuses
everything has not been tested either, and 22A W4-F2's lesson is that a check which cannot
notice a change proves nothing when it passes.

**This blocks W1, not W0.** §3.1 has W0 running the whole chain against a fixture-scale
source *before* the real source is touched, so every driver, freeze and test below is
complete and none of them read an uncleared byte.

### S22C-003 — the drivers, executed rather than described

[`scripts/campaign_22c.py`](../../../scripts/campaign_22c.py), and its fixture-scale run in
[`sprint-22c-w0-slice.json`](evidence/sprint-22c-w0-slice.json), integrity `dfee2af1c59faeb1…`.

Everything §1.2 lists is in one module — the cycle runner, the rolling replay harness, the
citation walker, the planted-update fixture and the fixture source — because five scripts
sharing a manifest, a store composition and a stage enumeration are one script wearing five
hats. What is **composed** rather than rebuilt is the load-bearing part:

| Stage | Composed from |
|---|---|
| register source | `CorpusFactory.ingest` — rights, licence, sensitivity, lineage, routing |
| extract | sealed proposals, revalidated by the released provider-revalidation legs |
| normalize | the released `SemanticExtractionProposal`, grounded in artifact bytes |
| cross-check | the pilots' own deterministic kernels through `run_descriptor_case` |
| quarantine | the released `CorpusQuarantineReason` vocabulary |
| compile | `SemanticExtractionService.commit` and `MemoryService.create` |
| evaluate | `run_descriptor_case` again, over every domain `registry.domain_ids()` names |
| promote | `SemanticPromotionGate.decide` then `SemanticMemoryService.transition_claim` |
| observe | the event store the other eight stages already wrote to |

The one thing the module adds is **sequence**, and the refusal that goes with it: `enter` is
the only way into a stage and it compares against `CAMPAIGN_STAGES` rather than a list
retyped at the call site, so "three completed cycles" is a countable claim rather than a
description. A pass that skipped a stage raises, and the record says which stage was due.

The slice ran all nine stages end to end at six segments across the two pilot domains:
source registered through the factory, six sealed proposals revalidated on the host with
**zero provider calls**, six claim structures grounded in loaded artifact bytes, six
deterministic cross-checks, one quarantine, five compiled memory records, a replay over
**all six** enumerated domains, five promotions through the released gate, and a citation
walk over **every** promoted artifact — not a sample — each of which resolved back to loaded
source bytes.

The record states in its own body that it **decides no exit criterion**: every 22C exit is a
claim about the real rights-cleared source across three cycles, so publishing the
pre-registration after this run is not publishing it after the numbers.

Two slice results are worth naming because they are the drivers refusing to flatter
themselves. Four of the six enumerated domains report `cases: 0` — reported rather than
omitted, which is W0-A1 below. And the plant's record says plainly that the released
`domains.checker` **accepted** its derivation, which is W0-F4.

### S22C-010 through S22C-018 — revision 1, frozen before the first cycle

[`sprint-22c-contracts.json`](evidence/sprint-22c-contracts.json) and
[`sprint-22c-pre-registration.json`](evidence/sprint-22c-pre-registration.json).

Nine sealed contracts: the five exit sentences verbatim, §2.2's five readings, the campaign
manifest contract, the §1.4 decision, and the fixture source with its recipes hash.
`measured_values: 0`, `thresholds_changed: 0`, `amendments_made_by_22c: 0` — structurally
zero, because 22C's plan contains no gate-owner amendment path at all — and a chronology of
five zeros.

The recipes are **imported from the modules that implement them and hashed from there**,
never retyped, so a driver that drifts drifts this record too and `--check` catches it. The
pin is on the readings and the source, not on the driver's bytes: 22B's W1-F2 cost a wave
when revision 1 pinned an implementation and W1's first act was a defect fix.

**The one thing 22B did not have to freeze.** §3.2 schedules this sprint around the risk
that the pipeline works perfectly and the artifact still does not move the holdout. A
holdout frozen as prose would let W3 discover, after three cycles, that its two arms were
never mechanically different — so the pre-registration runs the **arm mechanism** on a probe
case *deliberately outside the holdout set*. Arm A refused, arm B accepted by the released
checker with the expected answer, holdout still at `measured_values: 0`. The improvement
exit is now a comparison that can distinguish something, and that was established before a
single cycle was paid for.

[`sprint-22c-holdout.json`](evidence/sprint-22c-holdout.json) freezes the holdout itself:
four cases across both pilot domains, `domains.checker`, seeds, success definition, and the
two arms. Each case is a released pilot problem whose formal inputs deliberately omit
exactly one declared fact the source chapter supplies. Without it the kernel refuses the
case by design; with it the kernel solves and the *released* checker verifies the answer
independently, so a wrong value from a wrong artifact still fails. That is the existence
proof §4 describes and nothing more — the record says so in its own limitations.

### S22C-004 — the tests

| Module | Tests | What it holds |
|---|---:|---|
| `tests/cognitive_os/campaign/test_campaign_22c_drivers.py` | 23 | stage-order refusal, the four rights refusals, holdout separation, the two cross-check legs, the refusal-as-data guard, replay enumeration |
| `tests/cognitive_os/campaign/test_sprint_22c_w0_evidence.py` | 31 | the six seals, the live release verification, both bound repairs, `measured_values: 0`, the plant's record, the citation walk |

Four properties in that table are fences rather than tests. The **import fence** asserts that
`campaign_22c.py` contains no reference to `holdout_22c` at all, so a wave that reaches for a
holdout case as curriculum breaks the suite instead of the exit (22B W1-F6 made structural).
The **assertion-leg test** asserts that the released checker *accepts* the plant's
derivation, so a future wave that deleted the second cross-check leg would fail here rather
than quietly stop catching plants. The **stage-skip test** enters `normalize` after
`register_source` and requires a refusal. And the **citation test** requires every walked hop
to have loaded bytes whose recomputed hash equals the declared one, so a walk that degraded
into a field-presence check would fail.

Everything runs in memory against the two committed pilot packages, so it all runs in CI,
where no 22C store exists.

---

## W0 findings

Six findings, one decision, one carried observation. Three of the six were found only by
running the pipeline, and one of those three is a defect class that would have cost a cycle.

### W0-F1 — a wave command with 22C's environment loaded migrated the development database

`postgres_migrate.sh` calls `load_postgres_environment`, which sources
`.env.postgres.local` **with `set -a` after** the caller's own exports. Every variable that
file also defines therefore wins, `COGOS_DATABASE_ADMIN_URL` included. Running the migration
with 22C's environment sourced in the shell targeted `cognitive_os_dev`, not the store the
command was meant for. Nothing was damaged — the development database was already at head
`0015`, so `alembic upgrade head` printed no upgrade lines and was a no-op — but had it been
behind, a 22C wave command would have migrated the development store while reporting
success.

The variable that survives is the one `.env.postgres.local` does *not* define, which is why
the prefix guard still held and no database outside `cognitive_os_s22c` could have been
created. Fixed by invocation rather than by editing a released script: every 22C store
command runs with `COGOS_POSTGRES_ENV_FILE=.env.s22c.local`, and the four stores were
re-migrated that way and verified at head `0015` with 114 tables each. This is the mirror
image of 22B's `scale_22b.py` trap — there a driver *did not* source the env file; here a
script sources a *different* one over yours.

### W0-F2 — the released predicate registry has no vocabulary for acquired knowledge

`build_default_predicate_registry()` registers thirteen predicates — `project.*`,
`repository.*`, `task.*`, `verification.*`, `user.*`, `memory.*` — and then calls
`freeze()`. There is nothing under which a technical passage's worked result can be said,
and the registry cannot be extended after construction. A knowledge-acquisition campaign
stops at stage 3.

This is the seam §3.1 predicted, found by running the driver. It is **not** a released-code
change to fix: `PredicateRegistry` is publicly constructible and `register` is public before
`freeze`, which is exactly how `benchmarks/semantic_adapter.py` already builds a registry of
its own. The campaign registry is therefore *the released descriptors plus one*, so acquired
claims and released claims live under one vocabulary rather than two, and the consequence is
recorded rather than hidden: a campaign extraction's `registry_snapshot_hash` is not the
released snapshot hash and cannot be. That is 22A's S22A-030 decision — a registry that
gained something is allowed to say so — one layer down.

The predicate is `domain.worked_example`, functional and bitemporal, which also gives the
released functional-contradiction detector something real to say about two different results
for one topic.

### W0-F3 — the pipeline wrote semantic claims two stages before the check that judges them

**The wave's sharpest finding, and it cost one run to find.**

The first version of the driver committed each claim at **normalize**, stage 3. §9.1 does
not: it creates "semantic revisions" at **compile**, stage 6, two stages after the
cross-check. With the commit at stage 3 the planted passage's claim sat in the semantic store
as a proposed revision, and the released promotion gate's `semantic.critical_contradiction`
verifier then refused the **genuine** claim it contradicts. The run failed with
`chemistry-mass-balance: promotion rejected ['semantic.critical_contradiction']` — the true
claim blocked, the plant the cause.

The consequence generalises past this fixture and is worth stating plainly: **one planted
update would deny promotion to the very knowledge it falsifies.** A content attack becomes a
denial of acquisition, and no exit criterion as written would have noticed, because the plant
*was* quarantined and *did not* reach an active state. The four pipeline exits would have
read green while the pipeline was unusable.

Two repairs were tried before the right one. Retracting the quarantined claim through the
released lifecycle (`PROPOSED → RETRACTED`, legal, history-preserving) did not help: the
released functional detector compares current revisions and does not consult belief status,
so a retracted claim still contradicts. Closing its validity interval would have meant
choosing overlap semantics to suit the fixture. The actual fix was to stop writing at stage
3, which is what the development plan said in the first place — unverified content never
reaches the knowledge store at all, and stage 6 commits only what registration, extraction,
structuring, deterministic recomputation and quarantine have all cleared.

### W0-F4 — `domains.checker` accepts the plant, and it is right to

The obvious cross-check is to run the derived case through the released `domains.solve` tool
and `domains.checker` verifier and quarantine whatever the checker refuses. Running the
slice showed that check **passing the plant**, with `verifier_status: passed`.

It is not a defect in the checker. The checker judges whether the *derivation* is sound, and
the plant's derivation is impeccable: asked whether `2 H2 + O2 -> 3 H2O` balances, the kernel
correctly answers "no", the checker correctly accepts that answer, and the passage's
assertion that it *does* balance is never examined by anyone. A checker that accepts a case
has verified an arithmetic; nothing had verified the literature.

So the cross-check has two legs, and the record keeps them apart. The second compares the
conclusion the **source asserts** against the conclusion the kernel **computes**, and it is
what refuses the plant: `the source asserts structured.balanced=True; the kernel computed
False`. The slice record names the refusing leg precisely rather than crediting the checker,
and a test asserts the checker still accepts the derivation — so deleting the second leg
fails the suite instead of quietly ending plant detection.

### W0-F5 — a refused case raised out of the runner instead of being measured

`run_descriptor_case` has a branch for a solve that did not complete, and for the commonest
refusal of all — a kernel declining a case — that branch is unreachable. The released Tool
Plane records a `failed` event and then **re-raises** `ToolPlaneError`, so the exception
escapes. `UnsupportedProblemType` escapes even earlier, from the registry, and is a
`LookupError` rather than a `ToolPlaneError`.

Any harness that must *measure* refusals rather than merely avoid them would abort on the
first one: a replay over a domain with one malformed case, and — fatally for this sprint —
the holdout's arm A, whose entire point is that the case fails without acquired knowledge.
The improvement exit was unmeasurable until this was fixed.

Fixed once, in the one helper every 22C caller routes through, rather than in each of them:
cross-check, replay and both holdout arms need identical semantics and three copies of a
`try`/`except` is how two of them drift.

### W0-F6 — the pre-registration bound a hash that moved every run

`--check` failed deterministically on both runs. The pre-registration bound the contracts
record's `integrity_content_hash`, and that seal covers the whole body including
`recorded_at` — so the bound value changed every time either record was written, and the
binding asserted nothing.

This is 22B's W2-F1/F2 in a new place: never bind a value that moves with the clock. Fixed
by giving the contracts record a **substance hash** over its body excluding `recorded_at`,
which is what the pre-registration now binds; the full seal stays as the "this file is
intact" check. Both `--check` validators were then run twice and printed identical output on
the second run (22A W4-F3).

### W0-D1 — the §1.4 decision, taken in W0 as the plan requires

The plan's frozen default is taken: **the holdout evaluation runs end to end through
`domains.solve` and `domains.checker`**, resolving by problem type, and its outcomes are
sealed as 22C evidence records rather than `domain_pilot_runs` rows. **`0016` remains a
refusal**; no migration is allocated. 22A's W2-A1 stays carried by name, and W3-A1 is
untouched by any campaign work and stays carried.

This was decidable in W0 because nothing about it needed the source. §1.4 permits the gate
owner to decide otherwise, but only here — a persistence path appearing between cycle 1 and
cycle 3 would make the cycles measurements of different systems.

### W0-A1 — four of six enumerated domains retain no evaluation cases

`registry.domain_ids()` names six domains with both pilots registered, and the slice's
replay executed cases for two of them. The other four — `mathematics`, `physics`, `logic`,
`coding` — report `cases: 0`, reported rather than omitted, because "all retained domains"
is an enumeration the record must be able to be wrong about (22A W4-F1).

That is honest but thin: for four of six domains, "every cycle replays all retained domains"
currently replays nothing. The wave that reads the replay exit must either author retained
cases for the released four or state in the record that four of six retain none. Carried by
name rather than resolved here, because choosing which cases the released domains retain is
campaign-content work and this wave has no source.

---

## W0 evidence index

| Record | File SHA-256 | Integrity hash |
|---|---|---|
| [`sprint-22c-baseline.json`](evidence/sprint-22c-baseline.json) | `578a36f2ae88c035…` | `6ddd1e8950d7a923…` |
| [`sprint-22c-rights-gate.json`](evidence/sprint-22c-rights-gate.json) | `ea269719ded94cd5…` | `85e0b74a865b0da5…` |
| [`sprint-22c-holdout.json`](evidence/sprint-22c-holdout.json) | `690108b25c3ed412…` | `e9dd8fbf8961c9cc…` |
| [`sprint-22c-w0-slice.json`](evidence/sprint-22c-w0-slice.json) | `1287b09371af1d5f…` | `dfee2af1c59faeb1…` |
| [`sprint-22c-contracts.json`](evidence/sprint-22c-contracts.json) | `b343c0db131441a8…` | `d8c78d01e37c4502…` |
| [`sprint-22c-pre-registration.json`](evidence/sprint-22c-pre-registration.json) | `705f5d216843921a…` | `26b4199442cb211d…` |

Drivers: [`scripts/baseline_22c.py`](../../../scripts/baseline_22c.py),
[`scripts/rights_22c.py`](../../../scripts/rights_22c.py),
[`scripts/holdout_22c.py`](../../../scripts/holdout_22c.py),
[`scripts/campaign_22c.py`](../../../scripts/campaign_22c.py),
[`scripts/pre_registration_22c.py`](../../../scripts/pre_registration_22c.py). Contract:
[`src/cognitive_os/domain/campaigns.py`](../../../src/cognitive_os/domain/campaigns.py).

---

## W0 validation

`ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over `src
tests scripts infra`: clean. `mypy src/cognitive_os`: **no issues in 638 source files**.
`bandit -r src/cognitive_os`: no findings. `scripts/export_contract_schemas.sh --check`:
contract schema check passed. `scripts/check_repository_language.sh`: passed. Whole suite:
**4416 passed, 217 skipped**.

Both benchmark lanes no unit test covers were run locally before pushing, per the standing
rule that pytest green is not CI green: `sprint21c1-learned-ci` **16 cases, pass rate 1.0**
and `sprint21c1-learned-seed` **48 cases, pass rate 1.0**, both `learned-replay`. The
learned smoke ran `--confirm-isolated` against the 22C **integration** store with a scratch
artifact root — never the campaign store, whose fingerprint this sprint pins — and returned
healthy with `replay_matches: true` and no correlation or health failures.

Every sealer and `--check` was run **twice** and the second run is the one recorded (22A
W4-F3): `campaign_22c.py --check`, `rights_22c.py --check`, `holdout_22c.py --check` and
`pre_registration_22c.py --check` all reproduced on both runs, the last only after W0-F6 was
fixed.

**Exact-head CI: run [`31824921436`](https://github.com/palkouser/cognitive-os/actions/runs/31824921436),
head `e09857ab02b39fd35de2c572f1adb78dc5bfbfad`, 30 of 30 successful**, on
[PR #234](https://github.com/palkouser/cognitive-os/pull/234). The pull request exists
because the workflow triggers only on pushes to `main` and on pull requests, so a wave branch
receives no CI at all until one is open — which is why every sprint since 22A carries a PR
number, and why a wave that only pushed would have reported "green" against nothing.

---

## What W1 inherits

**Blocked, by name and with an owner:** the source-rights clearance. No sealed rights
record, no source; no source, no cycle 1. The record lists every field a concluded review
must produce, and the gate that will consume it is built and currently refusing. Nothing
else in this wave waits on it.

**Owed before any campaign number exists**, both with their reproductions bound by hash in
the baseline: 22B's **W3-F1** — `MemoryService.create` still commits the record and appends
`memory.item_created` in two transactions, confirmed unchanged in released code at
`application/services/memory_service.py`, and the fix must be proven by re-running 22B's own
crash to `items_missing_an_event == 0` — and 22B's **W4-F1**, a pre-registered post-restore
reindex procedure proven by re-running 22B's restore measurement to clustered recall back
over `0.95` from the sealed `0.9410`. A restore target, `cognitive_os_s22c_restore_test`, is
provisioned and waiting at head `0015`.

**Ready and frozen:** the nine-stage runner with its refusal, the replay harness over
`registry.domain_ids()`, the citation walker that loads bytes, the sealed plant, the campaign
manifest contract, and a holdout whose two arms are already known to be mechanically
different.

**Carried by name:** 22A W2-A1, 22A W3-A1, 22B W2-F2, and W0-A1 above.
