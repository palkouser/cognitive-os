# Gate D1 assessment — Experience Memory Graph and the pre-registered learning surface

- Sprint: 21D1
- Assessed: 2026-08-01
- Branch: `feature/sprint-21d1-learning-surface-emg`
- Parent baseline: `sprint-21c3-reality-baseline`, peeled to `05809446c726444146d85aad22808e10ce87ca3e`
- Migration head: `0015`, unchanged. `0016` remains unallocated.

## Verdict

**Gate D1 does not pass. Three of the twenty-one conditions are open: 6, 7 and 15.**

Two of them are the same measured negative result. No candidate learning surface on frozen C3
evidence reaches 200 eligible held-out outcomes or 20 changeable advisory decisions, so no
primary surface was pre-registered and none was fitted. The third is the retrieval usefulness
floor: the best bounded arm reaches 0.6750 top-5 recall against a required 0.70, and 0.4481
MRR@10 against a required 0.50.

None of the three is closed by tuning, and none was tuned. Under `§2.3` a null graph result
does not make the benchmark dishonest and does not require graph complexity to be added; the
loss is reported, the strongest simpler arm is named for D2, and FGW is rejected.

**Gate L2 remains closed.** Nothing was fitted, nothing was activated, and no threshold from
this sprint reaches a live decision.

## Condition by condition

| # | condition | status | handle |
|---|---|---|---|
| 1 | C3 tag, `origin/main`, both exact-head CI handles, branch protection, migration head and store isolation revalidated | **met** | `sprint-21d1-baseline.json`: tag object `497f959b…` matches the remote, both CI runs `30571166301` and `30572361952` conclude success at their exact heads, 27 required contexts with `enforce_admins`, head `0015`, three stores separated |
| 2 | all four candidate surfaces audited for leakage, label integrity, class balance, group structure, attribution, deterministic headroom, actionability, sample size and decision cost | **met** | `sprint-21d1-surface-audit.json`, four `SurfaceSampleAudit` records, each hash-bound; replay `python -m cognitive_os.learning.surfaces` |
| 3 | one primary and one secondary surface selected, pre-registration committed before held-out metrics are inspected | **met, with the primary declared unavailable** | `sprint-21d1-pre-registration.json`, `held_out_metrics_inspected: false`, decision hash `4ceeb74e…`. `SurfaceSelectionDecision` permits an absent primary only with a recorded reason, so the absence is explicit rather than silent |
| 4 | primary label is an independent accepted verifier outcome and the feature allowlist contains only pre-outcome data | **not applicable** | no primary label was pre-registered. The allowlist exists and is enforced: `FIELD_TIMING`, 21 fields, 13 pre-outcome |
| 5 | prohibited fields fail the leakage validator | **met** | `cognitive_os.learning.leakage.validate_query_projection`, stable reason codes, reusing `coding.reality_leakage.scan_for_control_leaks` rather than a second scanner |
| 6 | at least 200 unique held-out verifier-backed outcomes after deduplication and eligibility | **OPEN** | 214 outcomes exist and reconcile exactly (150 enumerated coding + 64 distinct accepted benchmark cases, `sprint-21d1-outcome-view.json`), but **0** remain eligible for any surface after the audit. `experience.correction_ranking`, the only balanced candidate, offers 120 against a threshold of 200, and the `§3.3` shortfall cap of 50 cannot close a gap of 80 |
| 7 | at least 20 primary-surface examples would change the advisory triage action | **OPEN** | 0 changeable decisions. `governed.outcome_triage` has a perfect oracle in `candidate_strategy` (1.0000) and, with both construction oracles removed, is exactly 60/60 on the coding half with no rung above 0.5000 and group frequency at 0.0000; the benchmark half is single-class. `experience.strategy_selection` has zero changeable decisions by construction |
| 8 | roles, groups, examples, features, labels, decisions, baselines, metrics, bootstrap and abstention immutable and hash-bound | **met** | every artifact is a hashed contract; the four-rung ladder and the seeded paired bootstrap (seed 21041, 2000 resamples, stdlib) replay from the committed outcome view with no database access |
| 9 | 60 historical coding pairs resolve every required event and artifact without mutating legacy manifests | **met** | `sprint-21d1-w3a-resolution.json`, 60 of 60, artifact hashes recorded before and after, 0 bytes modified |
| 10 | 20 fresh deterministic pairs cover logic and mathematics and pass byte-identical recompilation | **met** | `sprint-21d1-w3b-execution.json`, 10 + 10 distinct signatures, `FIXTURE_TIME` as the fixed epoch |
| 11 | at least 80 pairs, at least three domains, zero group crossing, 100% source resolution | **met** | `sprint-21d1-pair-set.json`: 80 pairs, 3 domains, 50 task signatures, 50 groups, 0 crossing |
| 12 | every correction edit script deterministically transforms its failed graph into the declared successful graph, canonical-hash verified | **met** | 80 of 80. Verification is structural, because provenance bytes differ between two runs of the same task; `structural_hash` exists for exactly this reason |
| 13 | malformed, cyclic, oversized, over-depth, secret-bearing, unresolved and poisoned graphs fail closed | **met** | 17 tests in `tests/cognitive_os/experience/test_graph_projection.py`, including the invariant holding with `networkx` blocked from `sys.meta_path` |
| 14 | all five arms run on the same frozen queries and group exclusions | **met** | `sprint-21d1-graph-queries.json`, 80 queries committed before any ranking, every query excluding its own group; `sprint-21d1-retrieval-benchmark.json` |
| 15 | unseen-task top-5 recall ≥ 0.70 and MRR@10 ≥ 0.50 for at least one bounded arm | **OPEN** | best arm 0.6750 recall and 0.4481 MRR@10. Reported, not tuned, per the pre-registered stop rule. The residual report shows the ceiling for any reranker over the current shortlist is 0.7625 |
| 16 | the graph arm reported against the strongest simpler arm even when it ties or loses, with deterministic ranking and explicit timeout counts | **met** | graph arm +0.1375 recall, +0.0089 MRR, **−0.0302 nDCG** against `minilm_vector`; 60 budget cutoffs reported; repeated-ranking agreement true |
| 17 | p95 ≤ 2 s, no comparison over 250 ms, at most 10 results | **met** | p95 1788.9 ms, per-pair timeout enforced at 250 ms with the budget reserved, 10 results returned; declared reference host recorded |
| 18 | graph results enter the Context Builder as hash-resolvable, verified, advisory, non-required, non-pinned candidates with no execution or acceptance authority | **met** | `ExperienceGraphContextRetriever`, 13 tests; candidates carry `content=None`, `pinned=False`, `required=False`, `evidence=False`; a non-advisory purpose receives nothing |
| 19 | FGW approved only if residual, benefit, budget, dependency and licence justify it; otherwise rejected with no new dependency | **met, as a rejection** | [ADR 0090](../../adr/0090-no-fused-gromov-wasserstein-and-the-shortlist-constraint.md). `git diff origin/main...HEAD -- uv.lock pyproject.toml` is empty |
| 20 | integrity, replay, restart, backup/restore, scratch-store matrix, schema, packaging, security, language and full regression checks pass | **met** | `sprint-21d1-verification-matrix.json`: 22 of 22 rows on their expected exit status, 306 s, evidence stores byte-identical before and after |
| 21 | protected release sequence, assessment, report, annotated tag and D2 handoff complete while Gate L2 remains closed | **met on completion** | this assessment, `sprint-21d1-report.md`, the D1 handoff, PR #217 merged under unchanged protection, exact-head `main` CI, annotated `sprint-21d1-emg-baseline` |

## What keeps the gate open, precisely

**Conditions 6 and 7 are one finding.** The C3 evidence does not contain a learnable advisory
surface. `governed.outcome_triage` looked like the obvious candidate and is not one: its label
is a function of a field that must not be a feature, and once both construction oracles are
removed the remaining signal is not merely weak but *anti-informative* — group frequency scores
exactly 0.0000. Sampling more of the same evidence does not fix a surface whose label is
determined by a forbidden field, which is why `S21D1-016` generated zero new outcomes.

**Condition 15 is a candidate-generation shortfall, not a ranking one.** Nineteen of the
twenty-six residual queries never had a relevant pair on the shortlist. Widening the shortlist
from ten to twenty raises the ceiling for any reranker from 0.7625 to 0.9750 at no dependency
cost. That is D2's first lever and it is why FGW was rejected now rather than deferred vaguely.

## Limitations carried forward

- Required approving reviews stay disabled because a second eligible reviewer does not exist.
  Carried from C3 unchanged, not worked around.
- 60 of 80 pairs are legacy and cannot be recompiled byte for byte.
- 14 of 20 fresh queries carry only a same-domain relevance judgement, reported as tier 2.
- The `postgres_bootstrap_roles.sh` `ALTER ROLE … NOSUPERUSER` abort is unchanged from C1/C2/C3
  and belongs to the bootstrap script's owner.
- No D2 holdout exists. Every number here is over the frozen D1 benchmark.
