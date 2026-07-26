# ADR 0084: Governed skill selection on the domain path, and the two-sided counterfactual

- Status: Accepted
- Date: 2026-07-25
- Sprint: 21, follow-up to [ADR 0083](0083-baseline-ladder-and-the-skill-selection-null-result.md)
- Relates to: [ADR 0073](0073-cross-domain-tool-authority.md) (cross-domain tool authority)

## Context

ADR 0083 recorded three follow-up items that the 21.6 measurement surfaced but did not
resolve, because each changes governed execution behaviour and deserved its own change:

1. `run_case_as_skill` never called `SkillSelectionService`. It took `entry.skills[0]` — the
   first name in the problem-type table — so the cross-domain path had no selection decision
   at all. The owner has confirmed this was not an intentional coverage boundary.
2. `SkillSelectionCandidate.statistics_score` was always 0, leaving ties to break on
   `str(skill_id)`.
3. The `useful` counterfactual label class was empty, guarded by a tripwire test.

## What was measured first

**Every problem type offers two candidate skills**, not one — 25 entries, all with two. So
`entry.skills[0]` was discarding a real choice on every case.

**For logic and mathematics the second candidate is unsatisfiable.** `constraint-solving`
requires `logic.satisfiable` and `cross-domain-result-review` requires
`generic.exact_value`; neither capability is ever emitted. So position 0 was the correct
answer — by luck, and unchecked. **For physics both candidates are satisfiable** (both
declare `physics.dimension`), which is a genuine tie nothing was resolving on merit.

**`useful` was not merely absent — it was impossible.** All 51 baselines are accepted, and
the `SELECTION_FORCED` variation *adds* a required capability, which only ever adds a
conjunct to the acceptance criterion. A monotone restriction cannot repair a rejected
baseline, so no corpus could ever have produced `useful` under that variation. The tripwire
was watching for something unreachable.

**`statistics_score` was not missing arithmetic.** `SkillExecutionService` already rebuilt
`SkillStatistics` after every execution, and the selector already computed
`accepted * 100 // executions` above a configured sample threshold. The gap was
*continuity*: `run_case_as_skill` built a fresh in-memory registry per case, so every
selection saw an empty execution log.

## Decision

### Selection runs, and the permitted set is enforced where it can be audited

`run_case_as_skill` now asks `SkillSelectionService` which skill to run.
`verifier_capabilities` is the case's own `required_verifiers` — the capabilities its checker
actually emits, and nothing wider — so a skill whose verifier will not run is excluded during
selection, with a recorded reason, rather than failing later in execution.

**Preconditions alone are not sufficient to scope selection, which the first run proved.**
Selection immediately chose `deterministic-arithmetic` for `long-multiplication`: it is a
mathematics skill, it declares `mathematics.numeric`, the case emits that capability, so every
precondition passed — and it is not in that problem type's permitted set. The problem-type
registry expresses a narrower authority than preconditions can.

So `SkillSelectionRequest` gains `permitted_canonical_names` (empty means unrestricted, which
is what every prior caller had), and non-permitted skills are recorded as
`SkillExclusionReason.NOT_PERMITTED`. **Restricting by exclusion rather than by pre-filtering
the candidate query is deliberate**: the decision record then states what selection was not
allowed to consider. A filtered query would have produced the same choice and a decision that
could not answer the question.

A post-selection guard in `run_case_as_skill` still raises if the chosen skill is outside
`entry.skills`. It is redundant with the request field on purpose — that guard is what caught
the defect above, and "preconditions should prevent this" is not a check.

`DomainSkillRun.selection` carries the decision so it is auditable, and `execution_id` is now
keyed by the selected revision as well as the case, because two different skills running one
case are two different executions — a fact the execution log's idempotency guard already
knew and the old derivation only got away with because the skill was fixed.

### Statistics decide ties, through the aggregation that already existed

`run_corpus_as_skills` shares one registry across a sweep, so the existing deterministic
aggregation reaches its sample threshold. Measured over the 17 physics cases: the first five
selections report `canonical_tie_break` (below the threshold of 5, honestly), and **12 of 17
then report `verified_statistics`**, with the winner holding the maximum score among
genuinely differing scores.

No learned component is involved, and none is wanted here. The requirement was a deterministic
aggregation over accumulated outcomes, and that is exactly what this is.

### The reported reason names the discriminating key

`SkillSelectionDecision.reason` was derived from the winner's own attributes: any candidate
with non-zero specificity reported `EXACT_SIGNATURE`, even when every candidate tied on
specificity and something further down the ordering decided. On the physics tie the record
claimed `exact_signature` while accumulated statistics were doing the work.

The reason is now computed by comparing the winner against the runner-up on the merit keys in
order, and reporting the first that differs. With a single candidate the ordering never ran,
so the winner's own scores are the only honest thing to report. Safety penalty, context cost,
and canonical identity map to `CANONICAL_TIE_BREAK`: if a cost key or a name decided, merit
did not.

### `useful` is settled by making impossibility unrepresentable

Two halves, because either alone would be misleading.

**`CounterfactualVariation` now knows which variations are monotone**, and
`CounterfactualLabel` refuses a `USEFUL` label for one. A harness that needs a three-valued
label is told at construction that its variation cannot produce one, instead of reporting an
empty class that a reader would take for a measurement.

**`learning/replacement.py` provides the two-sided variation.** `SELECTION_REPLACED` takes the
selector's choice as the baseline and executes a different permitted skill in its place —
through the ordinary governed selection path, by narrowing the permitted set to that one name,
never by bypassing selection. An alternative the selector refuses outright is recorded as a
rejected outcome rather than skipped, because forcing a skill the governed path will not select
means the task cannot proceed, and that is a real consequence.

Measured over all 51 cases: 51 labels, `useful=0`, `neutral=17`, `harmful=34`.

**`useful` remains empirically zero, and that is now a good property rather than a defect.**
It requires the selector to have chosen a skill that fails while an alternative succeeds. It
does not. The test asserts the distinction explicitly: reachable by construction, absent
because the selector does not err — and if it ever becomes non-zero, the selector has started
making a mistake worth investigating.

## Consequences

- The cross-domain path now has a governed, recorded, auditable selection decision where it
  previously had a table lookup. Every case still selects and is still accepted, so no
  outcome changed; what changed is that the choice is now checked.
- **Sprint 21B's null result stands unchanged.** The learned component tied a deterministic
  rule that was perfect on the corpus; making selection real does not create headroom,
  because the deterministic rule is now the *selector itself* and it is still correct. The
  `BaselineLadder` and out-of-distribution gates from ADR 0083 remain the durable output.
- `permitted_canonical_names` is a contract addition under D1, recorded here. It is
  backward-compatible: empty means unrestricted.
- Two schema changes follow: `SkillSelectionRequest` gains a field, and
  `SkillSelectionExclusion`/`SkillSelectionDecision` gain the new exclusion reason.
- The 969-label `SELECTION_FORCED` corpus remains valid and unchanged. It is a monotone
  corpus, which the contract now says out loud.
- **A latent bug was fixed on the way**: `execution_id` derived from the case alone would
  have collided the moment any caller ran two different skills against one case. Nothing did
  before, so nothing failed.

## Alternatives considered

- **Filter the candidate query to the permitted set.** Rejected: it yields the same choice
  and a decision record that cannot say what was excluded, which is the opposite of what a
  governance record is for.
- **Add a `task_type` precondition to all 19 skill packages.** Rejected: it duplicates the
  problem-type registry into 19 metadata files, so the two could drift.
- **Leave the tripwire and add fixtures whose baseline fails.** Rejected as the wrong
  diagnosis: under a monotone variation no fixture could produce `useful`, so this would have
  added cases to chase an unreachable class.
- **Compute `statistics_score` differently.** Rejected: the existing aggregation was correct
  and already written. Replacing working arithmetic to fix a lifetime problem would have left
  the lifetime problem.
