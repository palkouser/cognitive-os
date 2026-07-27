# Gate C1 assessment — Durable Learned Evidence

- Sprint: 21C1
- Gate: C1 — Durable Learned Evidence
- Branch: `feature/sprint-21c1-learned-evidence`
- Parent baseline: `e9001a9338c9507a60ca43f4e3e4bee7e28ef79b` (tag `sprint-21-substrate-baseline`)
- Implementation pull request: [#213](https://github.com/palkouser/cognitive-os/pull/213)
- Migration head: `0014`
- Evidence: [`evidence/sprint-21c1-local-matrix.json`](evidence/sprint-21c1-local-matrix.json)
- Decision: **conditional pass**, with the one open condition named in §3

## 1. Scope of this assessment

Gate C1 asks whether learned evidence is durable, replayable, auditable and safe. It does
not ask whether the system learns anything, and nothing below should be read as saying it
does. Every fixture used here is deterministic, the component it drives abstains
unconditionally, and no measurement in this sprint compares a learned component against
anything.

**Gate L2 remains closed.** §4 states what that means and what is still missing.

## 2. Conditions

Each condition from §2.2 of the Sprint 21C1 backlog, with the evidence that decides it.

### 2.1 Migration `0014` is the single Alembic head — **PASS**

`alembic heads` reports `0014 (head)`; `alembic check` reports no new upgrade operations.
Both were run after a full `downgrade base` → `upgrade head` cycle and a
`0014 → 0013 → 0014` cycle, all exit 0. Recorded as six rows in the local matrix.

The drift check is not free of history: Sprint 21R fixed an `alembic check` failure caused
by `0013`'s raw-SQL partial expression HNSW indexes, and the `include_object` hook that
resolved it is still in `infra/postgres/alembic/env.py` with three regression tests.

### 2.2 Learned evidence survives process and database restart — **PASS**

`scripts/learned_restart_smoke.sh` migrates to `0014`, ingests the fixture, restarts the
PostgreSQL container, and re-runs replay, health and artifact verification **in a new
process**. All three are identical across the restart, with `replayed_at` excluded because
it is the wall clock and comparing it would fail for the one reason that proves nothing.

The service-level half is proved separately: the smoke builds a *second*
`LearnedEvidenceService` over the same store and confirms it still reports the same active
component. If the service held authoritative state, that is where it would be lost.

### 2.3 Replay reproduces the persisted projection — **PASS**

`replay-verify` reports `projection_matches: true`, `hash_chain_verified: true`, no
failures, across 6 revisions. Replay is implemented independently in both stores and both
pass the same contract suite.

That it can *fail* is tested, not assumed. `test_postgres_health.py` corrupts the
projection, deletes a revision, opens a gap in the sequence, and breaks a payload hash;
each produces a named failure. Four benchmark seed cases do the same in memory.

### 2.4 Idempotency and conflicting reuse — **PASS**

Replaying an identical request returns the original record and appends nothing; reusing an
idempotency key with different content raises `IDEMPOTENCY_KEY_REUSED`. Enforced in the
contract suite for both stores, in the SQL controlled functions, and by a unique constraint
on `idempotency_key`.

Intake makes the asymmetry deliberate: the key covers source *identity*, the observation ID
covers identity *and content*, so re-offering the same outcome is free and the same source
presenting changed content fails closed.

### 2.5 Artifact lineage and visible corruption — **PASS**

Lineage resolves through the existing `ArtifactService`; bytes are never copied. Bit
corruption, a missing artifact, a hash mismatch and a size mismatch are each refused with a
named conflict, covered by `test_artifact_lineage.py` and five benchmark cases.

Health reports lineage rows referencing a missing artifact and rows whose hash disagrees
with the Artifact Store as integrity failures. Both required dropping a constraint to
inject, which is stated in the tests: the state health checks for is one a restored dump or
a partially applied migration can produce, not one the running system can.

### 2.6 Accepted, quarantined and rejected outcomes are distinguishable and auditable — **PASS**

All three statuses are stored, listable and counted separately in health. Every decision is
appended, including rejections — a refused outcome that left no trace would make the
quarantine queue a half-truth. Reason codes are stable enum values, not prose.

Quarantine review appends a replacement and leaves the original in place, verified by
`test_quarantine.py`. Reads of anything `internal` or `restricted` append an access record.

### 2.7 A real governed run cannot enter a training snapshot — **PASS**

Enforced in four independent places: the selection filter excludes them from the candidate
set; `LearnedDatasetRecord` refuses the combination; `ck_learned_training_excludes_real_runs`
refuses it in the database; and `LearnedObservationRecord.training_eligible` is false for
them regardless of status.

Verified positively as well as negatively: real runs *can* form an evaluation snapshot,
and a mixed corpus yields a training snapshot containing only the self-play members.

### 2.8 A fixture exercises the full lifecycle without enabling a useful model — **PASS**

`AlwaysAbstainingRanker` is driven through register → shadow → verified → activate →
disable → roll back, 6 revisions, in memory and against PostgreSQL. It abstains
unconditionally, so it cannot change any decision, and it is never packaged as a default.

`test_inert_lifecycle.py` states this in its own docstring, and no test in the sprint
asserts an accuracy or uplift number about it.

### 2.9 Activation is impossible without exact evidence — **PASS**

An activation must match, against stored state: component ID, revision, surface, artifact
lineage ID and hash, promotion-assessment identity and hash, and a positive human approval
identity and hash. Eight named defects are each refused — unauthorised actor, unrecorded
approval, unrecorded assessment, wrong assessment, wrong revision, refused approval, model
approver, unverified artifact — in tests and as benchmark cases.

Three structural properties back this up: `ACTIVE` is unreachable through
`advance_component` even where the transition table would allow it; `DISABLED -> ACTIVE` is
legal only when a rollback target is named; and `activation_actors` is empty by default, so
a shipped deployment can activate nothing whatever else is true.

### 2.10 Concurrent activation cannot create two active components per surface — **PASS**

Proved with two real database sessions, not two coroutines sharing a lock: exactly one of
two racing activations wins, the loser gets `STALE_REVISION` or `SURFACE_ALREADY_ACTIVE`
and appends no revision, and a direct query confirms one active row. The partial unique
index `uq_learned_components_active_surface` is the database half; health re-checks the
invariant and reports the index as missing if it is dropped.

### 2.11 Tables, grants, health, backup, restore and migration checks — **PASS**

9 tables, 8 append-only triggers, 10 controlled functions, 4 required indexes — all
asserted by health. `cogos_app` cannot insert into a ledger or update the projection; the
append-only triggers refuse the owner as well. Backup manifest and restore verification
carry learned counts, a history roll-up and four structural checks. The missing-artifact
negative case refuses as required.

The SQL and Python copies of the transition policy are compared exhaustively across all 72
combinations, so the second copy cannot drift unnoticed.

### 2.12 Credential-free CI remains deterministic — **PASS**

The `learned-evidence-core` job installs `--extra memory-postgres` and runs the learned
suite, the schema drift check, and both benchmark manifests — 16 CI cases and 48 fixed-seed
cases, 100% expected-policy match, zero provider, network, credential or GPU use. The
benchmark gate was shown to be non-vacuous: flipping one expectation fails exactly that
case and exits 1.

CI has been green at 28/28 on four successive pushes. One `postgres-integration` failure
was inspected and found to be `Initialize containers` — no checkout, no tests — and was
handled by re-running rather than by changing code.

### 2.13 The Section 0.1 release sequence is complete — **OPEN**

Steps 1–4 are complete: verified parent baseline, implementation and migration, local
evidence, and a pull request with all required checks green.

Steps 5–10 are not: merge, post-merge `main` CI, the final evidence update, the annotated
`sprint-21c1-evidence-baseline` tag, and tag verification. These are the release actions
this assessment precedes, and they cannot be self-referentially recorded here.

One limitation blocks a clean step 5 and is recorded rather than worked around: **the
repository has one collaborator, `palkouser`, so no second eligible reviewer exists.**
Required approving reviews were not enabled — the Sprint 21C1 backlog puts that out of
scope without a confirmed second reviewer — and no protection was weakened to compensate.
The 27 required checks and `enforce_admins` remain in force.

## 3. Decision

**Conditional pass.** Twelve of thirteen conditions pass with linked evidence. The
thirteenth, §2.13, is open only in the sense that the release actions it names have not yet
been performed; nothing in it is known to fail. It closes when the merge, post-merge CI and
tag verification complete, and the tag annotation carries their handles.

## 4. Gate L2 status

> Durable learned evidence is available, but useful learned behaviour has not yet been
> demonstrated.

Nothing was trained. No component is active in any shipped configuration. The only
component that reaches `ACTIVE` anywhere does so inside an isolated test or an isolated
`_test` database, and it abstains unconditionally.

Still required for Gate L2, unchanged by this sprint:

- enough real governed outcomes for meaningful evaluation;
- a trained candidate with reproducible artifacts;
- material uplift over the deterministic ladder;
- zero unacceptable confident out-of-distribution errors;
- no catastrophic forgetting;
- production-safe shadow performance;
- explicit activation authorisation for an actually useful component.

## 5. Residual risks

| Risk | Severity | Owner | Mitigation and status |
|---|---|---|---|
| No second eligible reviewer, so the implementation merges without independent review | Medium | Repository owner | Recorded, not worked around. 27 required checks and `enforce_admins` stay in force. Revisit when a second collaborator exists. |
| The development Artifact Store pair is inconsistent — 4 declared blobs missing, 5 orphan files, disjoint sets | Medium | Repository owner | Diagnosed read-only in wave 0; a non-destructive remediation is proposed and awaits operator approval. Untouched. All Sprint 21C1 evidence was produced on an isolated consistent pair. |
| The lifecycle transition policy exists in Python and in SQL | Low | Learning plane | Both are compared across all 72 combinations by `test_every_combination_agrees`; drift is a test failure. |
| Entering `SHADOW` and `VERIFIED` produces no correlated audit event | Low | Learning plane | Deliberate: no existing event type matches exactly, and inventing one was out of scope. The silence is declared in `STATE_EVENT_TYPES` and health reads the same map, so it is a known silence rather than an unexplained gap. |
| Health re-validates at most 1000 payload rows per ledger | Low | Operations | Bounded so health stays cheap enough to run often. Bulk artifact re-hashing lives in `artifact-verify`, which has no such bound. |
| A correlation warning could be mistaken for corruption | Low | Operations | Reported in a separate field that never affects `healthy`, with a documented recovery procedure that forbids back-filling events by hand. |

## 6. Deviations from the backlog

1. **Nine tables rather than eight.** `learned_activation_approvals` is separate from
   `learned_activation_history`, so a refused approval stays queryable and
   `ck_learned_approval_human_only` sits on exactly the rows it governs. Recorded in
   ADR 0086 as the one pre-approved schema deviation.
2. **Migration `0014` was corrected in place rather than superseded.** Three defects found
   in wave 3 — text-typed ledger appends, integer columns for boolean contract fields, and
   `descriptor_version` leaking into the revision payload — were fixed in the same
   migration. It is unmerged and exists on no deployed database, and one correct migration
   is easier to reason about than a released one plus a fix.
3. **The benchmark uses the existing runner.** The backlog permitted retaining focused
   tests if adapting the runner would need a second runner or a broad rewrite. It needed
   neither: one adapter function, one mode string, two manifests.
