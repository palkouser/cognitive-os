# Sprint 21C2 handoff — governed teacher and provider boundary

Sprint 21C1 built the durable evidence layer. Sprint 21C2 is where provider output first
becomes learned evidence, which is where the interesting failures start: material arriving
from outside the system, carrying rights and sensitivity it did not choose, into a store
whose whole value is that its contents can be trusted afterwards.

## 1. Starting point

| | |
|---|---|
| Parent tag | `sprint-21c1-evidence-baseline` |
| Parent tag object | `fc7bd5cf384890d036cd70149b4408de650c8ec8` |
| Parent peeled commit | `aed2c1b0af280d3f0924a37eeddc191cd320e936` |
| Parent final `main` CI | `30285564507`, successful |
| Parent migration head | `0014` |
| Next available migration | `0015` — only if Sprint 21C2 needs a schema change |
| Recommended branch | `feature/sprint-21c2-governed-providers` |
| Gate C1 | **pass**; the final release condition is closed by the verified tag annotation |
| Gate L2 | **closed** |

Start from the tag's peeled commit, not from a branch name, and verify the migration head
is `0014` before writing anything.

The implementation authority is the
[Sprint 21C2 Technical Backlog](sprint-21c2-technical-backlog.md).

## 2. The APIs Sprint 21C2 inherits

### Persistence

`LearnedEvidenceRepositoryPort` (`application/ports/learned_evidence.py`) — the only way to
touch durable learned state. Two implementations pass one shared contract suite; a third
would have to pass it unchanged.

- lifecycle: `register_component`, `advance_component`, `record_activation_step`,
  `get_component`, `list_components`, `component_history`, `active_component_for`
- lineage: `record_artifact_lineage`, `get_artifact_lineage`
- evidence: `record_evidence`, `list_evidence`
- datasets: `record_dataset`, `get_dataset`, `list_datasets`
- intake: `record_observation`, `list_observations`
- activation: `record_approval`, `get_approval`, `record_activation`,
  `get_activation_receipt`, `latest_activation_for`
- audit: `record_access`
- integrity: `replay`

Every mutation is idempotent on its key. Reusing a key with different content raises
`IDEMPOTENCY_KEY_REUSED`; that is the behaviour provider retry logic must be built around,
not around.

### Services

- `LearnedEvidenceService` — lifecycle, evidence, activation, rollback, audit. `activate`
  and `roll_back` require an actor named in `activation_actors`, empty by default.
- `LearnedObservationIntake` — `offer(reference, correlation_id)`; classification is a pure
  function, `classify(reference) -> (code, detail)`.
- `LearnedDatasetBuilder` — `build(surface, corpus_role, feature_schema_hash, …)`;
  deterministic, and rebuilding an identical selection returns the stored snapshot.
- `LearnedQuarantineReview` — `list_quarantined`, `review`. Human operators only.
- `LearnedArtifactStore` — `store`, `artifact_metadata`, `verify_artifact`,
  `build_lineage`. **No loader, by design.**

### Health

`PostgresLearnedHealthService.check() -> LearnedHealthReport`. Read-only.
`integrity_failures` makes the store unhealthy; `correlation_warnings` never does. Keep
that split — collapsing it makes an Event Store outage indistinguishable from learned-state
corruption.

## 3. Provider output fields that must map into learned evidence

Provider output is a governed outcome like any other, and enters through
`GovernedOutcomeReference`. Sprint 21C2 must supply every field below; none has a safe
default, which is why none has one.

| Field | Requirement |
|---|---|
| `surface` | The decision surface the output is about. |
| `source_kind` | Must be a *new* provider-specific kind. **Do not reuse an existing entry in `REAL_GOVERNED_SOURCE_KINDS`** — see §5. |
| `source_task_id` / `source_run_id` / `source_event_id` | At least one. An outcome nobody can trace back is refused by the contract. |
| `source_payload_hash` | Hash of the provider output as recorded, resolved without modifying the source record. |
| `provenance_class` | Provider output is not a real governed run unless a governed run actually produced it. |
| `attribution` | `UNKNOWN` quarantines rather than rejects, which is the right default when a provider's contribution to an outcome is unclear. |
| `usage_rights_verified` | False rejects. Provider terms, licence and any customer-data restriction must be resolved *before* intake, not recorded as a caveat after it. |
| `sensitivity` | One of `public`, `internal`, `restricted`. An unrecognised label quarantines, because it decides whether reads are audited. |
| `verifier_status` / `verifier_evidence_hash` | Required for verifier-backed source kinds. |

**Retention and expiry have no representation yet.** `LearnedObservationRecord` has no
retention or expiry field, and Sprint 21C1 deliberately did not invent one without a use
case. If Sprint 21C2 needs provider output to expire, that is a contract change and
migration `0015`, and it should be designed against a concrete retention obligation rather
than a general sense that one is needed.

## 4. Accepted Gate C1 limitations

1. **No second eligible reviewer.** One collaborator. Required approving reviews are not
   enabled, and no protection was weakened to compensate. If Sprint 21C2 adds a
   collaborator, enabling reviews is the first thing to do.
2. **Two lifecycle states are uncorrelated.** Entering `SHADOW` and `VERIFIED` produces no
   audit event, because no existing event type matches exactly. Declared in
   `STATE_EVENT_TYPES`; if Sprint 21C2 adds matching event types, health picks them up from
   the same map.
3. **Health re-validates at most 1000 payload rows per ledger.** Bulk artifact re-hashing is
   in `learned.py artifact-verify`, which is unbounded.
4. **The release sequence is closed.** The merge, successful post-merge CI, and remote
   annotated tag verification closed the thirteenth Gate C1 condition. The immutable
   handles remain in the tag annotation.

## 5. Boundaries Sprint 21C2 must not cross

These are not preferences. Each is enforced by a contract, a database constraint or both,
and each exists because the failure it prevents is silent.

- **No provider may approve an activation.** `LearnedApprovalAuthorityKind.MODEL` and
  `PROVIDER` exist so a self-approval can be *named and refused*, not so it can be
  configured. `ck_learned_approval_human_only` refuses it in the database too.
- **No provider may review its own quarantined evidence.** Same failure, same refusal.
- **No provider output may be classified as a real governed run unless a governed run
  produced it.** `REAL_GOVERNED_SOURCE_KINDS` is an allowlist; adding a provider kind to it
  would make provider output the yardstick every later comparison is measured against.
- **No provider output may enter a training snapshot if it is a real governed run.**
  Enforced four times over; do not add a fifth path around it.
- **Persistence is not authorisation.** A learned component does not become activatable
  because its evidence is now durable. `activation_actors` stays empty until something
  worth activating exists and a human authorises it.
- **No artifact is deserialised.** Provider output arrives as data. If Sprint 21C2 needs to
  interpret a provider artifact, that is a new component with its own threat model, not a
  loader added to `LearnedArtifactStore`.
- **No provider writes active memory.** Provider output becomes an *observation*, which is
  a classified reference. Whether it ever becomes anything more is a separate, evidenced
  decision.

## 6. Unresolved item carried forward

**The development Artifact Store pair is inconsistent** — 4 declared blobs missing, 5 orphan
files, disjoint sets. Diagnosed read-only in Sprint 21C1 and deliberately untouched; a
non-destructive remediation is proposed in
[`evidence/sprint-21c1-artifact-mismatch-inventory.json`](evidence/sprint-21c1-artifact-mismatch-inventory.json)
and awaits operator approval.

Do not repair it as a side effect of Sprint 21C2. Either side may be the recoverable one,
and a destructive fix to make a verifier pass would destroy the evidence needed to decide.

## 7. Gate L2

Still closed.

> Durable learned evidence is available, but useful learned behaviour has not yet been
> demonstrated.

Sprint 21C2 makes provider output *available* as governed evidence. That is upstream of
Gate L2, not a step through it. Opening Gate L2 needs enough real governed outcomes to
evaluate against, a trained candidate with reproducible artifacts, material uplift over the
deterministic ladder, acceptable out-of-distribution behaviour, no catastrophic forgetting,
safe shadow performance, and an explicit authorisation to activate something actually
useful. None of those is a Sprint 21C2 deliverable unless Sprint 21C2 says so explicitly.
