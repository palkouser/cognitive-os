# ADR 0083: The baseline ladder, and the recorded null result on skill selection

- Status: Accepted
- Date: 2026-07-25
- Sprint: 21, phases 21.6 and 21.7
- Relates to: [ADR 0081](0081-learning-substrate-extension-seam.md) (extension seam)

## Context

Phase 21.6 asked whether a learned component beats the deterministic baseline on the
skill-selection surface. Phase 21.7 asked whether anything should be promoted.

The corpus was the 969 counterfactual labels phase 21.1 produced: for each of 51 fixture
cases, each of 19 seed skills forced in turn, labelled `neutral` (outcome unchanged) or
`harmful` (outcome broken). The class balance was non-degenerate at 56.0 % majority, which
is why the phase proceeded.

## What was measured

Before writing any model, three questions were put to the corpus.

**1. Is the label predictable from data already declared before the run?** Yes,
perfectly. The rule *harmful iff a candidate's declared verifier capability is absent from
the case's `required_verifiers`* scores **1.000 on all 969 labels** — 543/543 harmful,
426/426 neutral, zero errors. `required_verifiers` is a field on `DomainBenchmarkCase`,
populated before execution.

**2. Is there case-level variation to learn?** No. The label is a pure function of
`(domain, candidate)`: 57 groups, none ambiguous. The capability vocabulary is disjoint per
domain — `logic.*`, `mathematics.*`, `physics.*` — with two capabilities each.

**3. Does the deterministic path already implement this?** Yes.
`SkillSelectionService._requirements_available` performs exactly that subset test against
`SkillApplicabilityInput.verifier_capabilities`. The reason harm was observable at all is
that the domain path never calls `SkillSelectionService`: `run_case_as_skill` resolves the
skill by static lookup (`resolve(case.problem_type).skills[0]`) and executes that exact
revision. **There is no selection decision on this path to improve.**

### The ladder result

| Split | majority (trivial) | `requirements_available` (deterministic) | kNN (learned) |
|---|---|---|---|
| group-aware by case | 0.5666 | **1.0000** | 1.0000 |
| held-out domain: logic | 0.5789 | **1.0000** | 0.8947 (32 confident errors) |
| held-out domain: mathematics | 0.5263 | **1.0000** | 0.8421 (54 confident errors) |
| held-out domain: physics | 0.5789 | **1.0000** | 0.8947 (34 confident errors) |

Out-of-distribution total: 969 evaluated, **0 abstentions, 120 confident errors**.

## Decision

**Record a null result on the skill-selection surface, and build the machinery that makes
that conclusion mandatory rather than a matter of care.**

The plan sanctions the outcome — "a recorded null result is a valid 21.6 outcome; the
substrate's value does not depend on it" — but the outcome is not the interesting part.
The interesting part is that a model here would have looked excellent.

### The straw-man trap was live, and is now closed structurally

Against the majority class the kNN scores 1.000 versus 0.5666 — a 43-point apparent win.
Against the correct baseline it ties. `LearnedPromotionAssessment.baseline_metric` was in
effect free text: any caller could pass 0.5666, clear a 0.05 improvement threshold, and
reach eligibility with a component that adds nothing.

Two contracts close it:

- **`BaselineLadder`** records every comparison actually run and **refuses to validate
  without a `DETERMINISTIC` rung**. A ladder of trivial baselines is rejected as a straw
  man at construction.
- **`LearnedPromotionAssessment.baseline_metric` is pinned** to
  `baseline_ladder.strongest_non_learned`. The check runs *whatever the decision is*, so a
  recorded rejection must also state the true baseline — otherwise the null result itself
  could understate what the component was up against.

A learned rung can never raise the bar it must clear: `strongest_non_learned` excludes
`LEARNED` rungs by construction.

### The abstention requirement needed a measurement, not a field

`LearnedComponentDescriptor.supports_abstention` records that a component *can* abstain.
It says nothing about whether it *does* when it should. The kNN declares
`supports_abstention=True`, has a similarity floor and a neighbour-agreement term, and
still answered confidently and wrongly 120 times on domains it had never seen — because
Jaccard overlap stays high on `problem_type` and `candidate` while the capability
vocabulary is entirely disjoint.

**`OutOfDistributionAssessment` makes that a gate.** Every domain is held out in turn,
confident errors are counted, and `abstains_when_ignorant` is false if any occurred.
Eligibility requires it. The field is mandatory on the assessment, not optional, because an
optional gate is skipped by omitting it.

Worth stating plainly: the agreement term was *my* mitigation for this failure, and it
raised accuracy from 0.737 to 0.84–0.89 without producing a single abstention. It did not
work. The gate catches what the mitigation missed, which is the argument for having the
gate rather than trusting the design.

### The ladder stopped below the parametric tiers, deliberately

The trial order is constant/majority → kNN → decision tree → random forest → gradient
boosting. It stopped at the deterministic rung, because that rung scores 1.000 and nothing
above it can do better than tie. Consequently **`scikit-learn`, `xgboost`, `scipy`, and
`joblib` were not installed**, and no `learned-baseline` or `learned-boosting` extra was
added to `pyproject.toml`.

Installing a gradient-booster to tie a two-line subset test would have added a dependency
tree to prove a negative. `LadderReport.ladder_stopped_at` and `stopped_reason` record
where the climb stopped and why, so the omission is a stated result rather than an
oversight.

Tier A needs no optional extra at all: similarity is a set intersection over the
categorical encoding, in pure Python, and `ExperienceKnn.descriptor.required_extra` is
`None`.

### A false claim in Sprint 21A was corrected

`learning/selfplay.py` asserted that the deterministic selector "cannot predict" the
consequence being labelled, "because which checks a problem type emits is a runtime
property". That was an assertion where a measurement was needed, and it is wrong: the
capabilities are fixed per domain and the case declares them. The docstring now records
the correction and the number that refutes it.

## Consequences

- **No component is promoted.** Gate L condition 8 closes as a reproducible no-go, which
  the plan permits as a valid closure.
- **The substrate is proven by a rejection.** Both safety gates passed on this run —
  retention `retained`, invariance `identical` — so the recorded decision
  (`abstention_unsupported`) is about the component having no value, not about the
  machinery failing. A gate stack that only ever passes is untested.
- **Tier A remains first in the trial order.** Nothing measured here counts against it;
  what was measured is that *this surface* has no headroom, and that a corpus whose labels
  are a closed-form function of declared data cannot demonstrate otherwise.
- **The tripwire inverts.** `test_the_deterministic_rule_is_perfect_on_this_corpus` fails
  if a future corpus makes the rule imperfect. That failure is the signal that real
  headroom has appeared and the ladder should climb further.
- **Three surfaces have now been measured and found unlearnable**, each for a different
  reason: context reranking (all candidates required and pinned), skill ranking (the
  revision was ignored, so every label was neutral), skill selection (the label is a
  closed-form function of declared data, and no selection happens on the path). The
  pattern is that a governed deterministic system leaves narrow room for learned
  decisions, and finding the room requires measuring the surface before building on it.
- **`DistributionComparison` is produced with zero real-run evidence**, verdict
  `not_established` against a declared threshold of 100. Gate L condition 7 asks for
  measurement and disclosure, not for low divergence; "we do not know" is the honest
  reading and the contract refuses any other.

## Alternatives considered

- **Weaken the baseline to the majority class and promote the kNN.** This is the trap,
  named explicitly so it cannot be reached by accident. It would have produced a
  promoted component with a 43-point headline improvement and no value whatsoever.
- **Synthesise a harder corpus so a model has something to beat.** Rejected: a corpus
  built to make a model look necessary measures the corpus builder, not the model. The
  surface's emptiness is the finding.
- **Install scikit-learn and run the full trial order anyway, for completeness.**
  Rejected: every rung above the deterministic one can at best tie 1.000, so the
  additional dependencies would buy no information.
- **Fix the domain path to call `SkillSelectionService`, creating a real selection
  decision.** Plausible, and out of scope here: it changes governed execution behaviour
  on a path Sprint 20 closed, which needs its own controlled change rather than being
  smuggled in as a side effect of a learning experiment. Recorded as follow-up work.
