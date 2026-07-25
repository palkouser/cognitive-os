# Cross-domain pilot benchmarks

## Layering

| Manifest | Cases | Requires |
|---|---|---|
| `sprint20-domain-ci.yaml` | 24 | nothing — offline, CPU-only, no extras |
| `sprint20-domain-seed.yaml` | 120 | nothing — offline, CPU-only, no extras |
| `tests/integration/postgres/test_domain_postgres.py` | 8 | opt-in PostgreSQL 18 |

Optional live-provider and Inspect AI adapters are out of Sprint 20 scope; the acceptance authority
stays with Cognitive OS.

## Distribution

CI, 24 cases:

| Group | Cases |
|---|---|
| Mathematics | 6 |
| Physics | 6 |
| Logic | 6 |
| Transfer and governance | 6 |

Seed, 120 cases: 30 mathematics, 30 physics, 30 logic, 30 transfer, adversarial, and governance.

## Scenarios

| Scenario | Meaning |
|---|---|
| `accept` | the correct answer must be accepted |
| `reject` | a deliberately wrong answer must be rejected |
| `transfer` | the disposition must match the declared expectation |
| `governance` | an authority or safety invariant must hold |

The adapter executes each case rather than consulting a table, so a case passes only when the
harness actually behaves as declared.

## Governance invariants

Twenty-eight invariants run in both manifests and as parametrised tests.

Governed execution:
`controller_owns_plan`, `tool_plane_audits_solve`, `controlled_path_rejects_wrong`,
`required_context_enforced`, `skill_engine_verified_only`, `routing_signature_tool_only`.

Learning-plane integration:
`learning_recorded_events_only`, `learning_failure_preserved`, `learning_corpus_rights`.

Weakness, proposal, and controlled change:
`weakness_from_recorded_failure`, `proposal_traces_to_weakness`, `change_cannot_self_promote`.

Safety, authority, and determinism:
`unsupported_problem_type`, `forbidden_operation`, `raw_text_rejected`, `expression_bomb_bounded`,
`unknown_not_unsat`, `incompatible_units`, `offset_units_exact`, `core_without_extras`,
`transfer_controls_required`, `hard_gate_blocks_positive`, `runtime_cannot_release`,
`evidence_immutable`, `exact_not_approximate`, `nan_rejected`, `missing_verifier_blocks`,
`underdetermination_reported`.

## Measured results

All 24 CI and all 120 seed cases pass their expected disposition. Across the 51 underlying fixture
cases, on every path:

| Path | Correct accepted | Wrong rejected |
|---|---|---|
| Direct solver and checker | 51/51 | 51/51 |
| Cognitive Controller + Tool Plane | 51/51 | 51/51 |
| Skill Engine (exact `VERIFIED` revision) | 51/51 | 51/51 |

| Arm | Mathematics → physics (skill) | Mathematics → logic (strategy) |
|---|---|---|
| Target baseline | 0.647 | 0.625 |
| No-skill control | 0.647 | 0.625 |
| Unchanged source revision | 1.000 | 1.000 |
| Minimally adapted | 1.000 | 1.000 |
| Domain-specific | 1.000 | 1.000 |
| Source retention | 1.000 | 1.000 |
| Unrelated domain | 1.000 | 1.000 |
| **Target delta** | **+0.353** | **+0.375** |
| Hard gates | none breached | none breached |
| Disposition | `positive_transfer` | `positive_transfer` |

The narrow-optimisation fixture is rejected as `negative_transfer` on the cost-ratio gates.

## Learning-plane results

Every one of the 51 fixture cases, run under the Controller and Tool Plane, compiles through the
unmodified Experience Compiler:

| Path | Compilation decision | Terminal state | Candidates |
|---|---|---|---|
| Accepted run | `completed`, 51/51 | `accepted` | `memory`, `semantic_observation`, `benchmark_case`, `corpus_item` |
| Wrong-answer run | `completed`, 51/51 | `rejected` | adds `failure_pattern`, `negative_example` |

Full ingestion — compile, memory write, semantic extraction, corpus declaration — produces, per run:
2 memory revisions, 4 semantic observations, 4 semantic claims, and at least 1 corpus item (2 on the
wrong-answer path). Corpus usage-rights declarations mirror the case's own `ProvenanceRef`:
`REDISTRIBUTION` and `PUBLIC_RELEASE` match `redistributable`, and `MODEL_TRAINING` and
`COMMERCIAL_USE` stay undeclared.

## Weakness, proposal, and controlled-change results

Three legitimate `polynomial-equation` inputs with irrational roots — a real, registry-accepted
input the exact-rational solver genuinely cannot answer — are run through the governed Controller and
Tool Plane path and each fails there for real:

| Stage | Result |
|---|---|
| Probes run | 3/3 produce a recorded `tool_call.failed` and a rejected acceptance decision |
| Mining | 3 signals group into 1 weakness signature; `WeaknessType.MISSING_SKILL` |
| Confirmation | explicit `CANDIDATE -> CONFIRMED` transition, `reproducible` |
| Proposal | `TOOL_DEFINITION_CHANGE`, reaches `approved_for_experiment` |
| Isolated experiment | `declarative_copy` isolation, network disabled, 1 file in scope, 15 evaluation gates, 0 hard failures |
| Assessment | `requires_manual_review` — tier 3, no runtime promotion authority |

Mining and the full cycle are deterministic: two independent runs produce identical mining manifests
and byte-identical experiment, isolation, and assessment content hashes, because mined-signal identity
is derived from the case and the observed control-flow shape, not from per-run event-payload hashes
that would otherwise carry a fresh timestamp every execution.

## Determinism

Cost is modelled from tool calls, not timed, so dispositions and deltas are byte-identical across
runs. Repeated executions of both manifests produce identical statuses and metrics. Reported
wall-clock time appears only in the smoke report and never in stored evidence.

## Provenance

Every case carries a `ProvenanceRef`: source `cognitive-os/sprint-20-fixtures`, Apache-2.0,
redistributable, authored for Sprint 20 and derived from no public benchmark set. There is no
contamination path from a published evaluation set, and no third-party benchmark material is
redistributed.
