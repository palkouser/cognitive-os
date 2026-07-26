# ADR 0086: Learned evidence persistence and its authority boundaries

- Status: Accepted
- Date: 2026-07-26
- Sprint: 21C1
- Stage gate: Gate C1 — Durable Learned Evidence
- Relates to: [ADR 0081](0081-learning-substrate-extension-seam.md) (learning substrate seam),
  [ADR 0082](0082-approximate-vector-retrieval-and-capacity-envelope.md) (approximate retrieval),
  [ADR 0083](0083-baseline-ladder-and-the-skill-selection-null-result.md) (baseline ladder),
  [ADR 0085](0085-coding-domain-as-fourth-cross-domain-domain.md) (coding domain)

## Context

Sprint 21 released a learning substrate whose contracts are sound and whose state is
entirely in memory. Every corpus, ladder, assessment, invariance proof and capacity
envelope disappears when the process exits. That is acceptable for a substrate that has
never activated anything, and unacceptable for everything that follows: a promotion
decision that cannot be replayed is not evidence, and an activation that cannot be rolled
back is not governed.

Sprint 21C1 adds durability. It deliberately adds nothing else. No component is trained,
no component is activated for benefit, no provider is contacted. The risk this ADR exists
to prevent is that "we can persist learned state" gets read as "the system learns".

## Decision

### One authority per concern

| Concern | Authority | Not the authority |
|---|---|---|
| Artifact bytes and base artifact metadata | the existing Artifact Store and `artifacts` table | learned tables, which hold references only |
| Learned lifecycle history | append-only `learned_component_revisions` | the projection, the Event Store, or in-memory registry state |
| Current learned component state | `learned_components`, rebuilt from lifecycle history | any in-memory cache |
| Learned domain invariants | `cognitive_os.domain.learned` contracts and `LearnedComponentRegistry` policy | the database alone, or the service alone |
| Cross-subsystem audit | the existing Event Store | learned tables |
| Runtime activation lookup | the persistent learned projection through the learned service | the registry's in-memory map |

The consequence that matters: **the Event Store is not a second learned-state authority.**
A missing correlated event is an integrity *warning*, because the learned history is
still complete and replayable. A projection row without lifecycle history is an integrity
*failure*, because the authority itself is gone. Health reports the two differently, and
the difference is asserted by tests rather than left to interpretation.

### One typed evidence table, not nine

`learned_evidence_records` stores predictions, shadow results, invariance proofs,
forgetting assessments, distribution comparisons, capacity envelopes, baseline ladders,
OOD assessments and promotion assessments under an allowlisted `evidence_kind`.

Nine tables was the obvious alternative and was rejected. The contracts are all
hash-bound, append-only, payload-carrying records whose only structural difference is
which contract validates the payload; nine tables would multiply constraints, triggers,
grants and health checks by nine to express one shape. The allowlist keeps the type
system honest: an unknown `evidence_kind` fails validation in the domain layer *and* a
CHECK constraint in the database, so an unrecognised record cannot be stored and later
mistaken for evidence.

The cost is that querying one evidence kind requires a predicate rather than a table
name. That is a query-planning concern with an index, not a correctness concern.

### Nine tables, not the eight the backlog named

The Sprint 21C1 backlog specifies eight tables and folds activation approvals into
`learned_activation_history`. The implementation separates `learned_activation_approvals`
into its own table, which is the one pre-approved schema deviation this ADR records.

The reason is auditability, not tidiness. An approval is evidence about a *human
decision*, with its own lifetime: it is issued before an activation, it may be refused,
and a refused approval must remain queryable as proof that the refusal happened. Folding
it into the receipt ledger would mean either a receipt row that represents no state
change, or a nullable approval block on every disable and rollback row. Separating it
lets `ck_learned_approval_human_only` sit on exactly the rows it governs, so
"a model cannot approve" is one constraint on one table rather than a conditional
predicate on a mixed ledger.

`learned_activation_history` still holds the approval identity and hash on the activation
row, so the exact-evidence binding is unchanged.

### Artifact bytes stay where bytes already live

Learned persistence stores lineage — a reference to an existing `artifact_id`, the
declared format and media type, the declared hash, and the observed hash at verification
time. It never stores the bytes. Deduplication, content addressing and backup coverage
therefore keep working exactly as they already do, and there is no second copy to drift.

**No artifact is ever deserialised.** `LearnedArtifactFormat.JOBLIB` remains in the enum
as a descriptive legacy value, and Sprint 21C1 contains no code path that loads it.
Verification reads bytes and hashes them; it does not interpret them. An artifact is
data, and a loader that executed an object graph supplied as data would convert every
lineage record into a remote-code-execution surface.

### Every mutation is one transaction and one receipt

A learned state mutation atomically validates the expected current revision, appends one
immutable history row, updates the projection, and returns a hash-bound receipt. The
correlated Event Store event is emitted afterwards through the existing event service.

This is deliberately *not* a distributed transaction and deliberately *not* a new outbox
framework. If the event append fails, the learned history is still authoritative and
complete, and health surfaces the correlation gap. Introducing a second generic
reliability mechanism to close a warning-level gap would add more failure modes than it
removes.

### Replay is the integrity test, not a recovery script

Replay reads append-only history in stable component/revision order, validates the hash
chain and the legality of every transition, and reproduces the projection exactly. It
fails closed on a missing revision, a broken predecessor, an illegal transition or a hash
mismatch. It mutates nothing, so it is usable as a health check against a live database.

If replay and the projection disagree, the projection is wrong by definition. That is the
operational meaning of "history is the authority".

### Activation requires exact evidence, and rollback is a distinct operation

Activation fails unless component ID, revision, surface, artifact-lineage ID and hash,
eligible promotion-assessment ID and hash, and a positive human approval ID and hash all
match exactly. It also fails when the revision moved after the assessment, when artifact
verification is stale, when another component already holds the surface without an atomic
replacement request, when the component is retracted, when the actor lacks authority, or
when the approver is a model or provider identity — a component must not approve itself.

Rollback is a separate domain operation that restores only the exact prior activation
named by the current activation chain, after re-verifying that activation's artifact,
promotion and approval hashes. The generic registry `transition` continues to reject
`DISABLED -> ACTIVE`, so there is no path that reaches ACTIVE without either full
activation evidence or an explicit, verified rollback.

At most one component is active per surface. This is enforced twice: by the service, and
by a partial unique index, so a concurrency bug cannot produce a committed state with two
active components.

### The default configuration activates nothing

`config/learned.example.yaml` declares persistence enabled and an empty active-component
set. Persistence support for activation is not authorisation to activate. The inert
deterministic fixture used to prove lifecycle persistence enters ACTIVE only inside
isolated tests and is never packaged as a default runtime component.

## Gate C1 is not Gate L2

Gate C1 asks whether learned evidence is durable, replayable, auditable and safe. Gate L2
asks whether the system learns anything useful. Passing the first says nothing about the
second, and the Sprint 21C1 report must state so in those words.

What remains missing after Gate C1: enough real governed outcomes to evaluate against, a
trained candidate with reproducible artifacts, material uplift over the deterministic
ladder, acceptable out-of-distribution behaviour, no catastrophic forgetting, safe shadow
performance, and an explicit authorisation to activate something that is actually useful.

## Alternatives considered

- **Persist through the Event Store alone, projecting learned state from events.** Rejected:
  it makes the audit stream load-bearing for learned correctness, so an event-append
  failure becomes a learned-state failure, and every learned query becomes a projection
  rebuild. The Event Store is a good audit spine and a poor transactional authority for a
  subsystem that needs compare-and-swap.
- **One table per evidence contract.** Rejected above: nine times the schema surface for
  one shape.
- **Store model bytes in a `learned_artifacts` BYTEA column.** Rejected: it duplicates the
  Artifact Store, breaks content-addressed deduplication, and doubles what backup must
  carry.
- **Allow `DISABLED -> ACTIVE` for rollback.** Rejected: it would make the single most
  dangerous transition reachable by the generic API, and the registry's refusal is one of
  the few structural guarantees the substrate already has. A separate rollback operation
  with its own evidence requirements keeps that refusal intact.
- **Repair the development Artifact Store mismatch as part of this sprint.** Rejected: the
  metadata and the filesystem have drifted into disjoint sets, either side may be the
  recoverable one, and a destructive "fix" to make a verifier pass would destroy the
  evidence needed to decide. Sprint 21C1 diagnoses it read-only, proposes a recoverable
  remediation for operator approval, and builds its release evidence on an isolated,
  consistent pair.
