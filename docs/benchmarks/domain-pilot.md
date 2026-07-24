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

Sixteen invariants run in both manifests and as parametrised tests:

`unsupported_problem_type`, `forbidden_operation`, `raw_text_rejected`, `expression_bomb_bounded`,
`unknown_not_unsat`, `incompatible_units`, `offset_units_exact`, `core_without_extras`,
`transfer_controls_required`, `hard_gate_blocks_positive`, `runtime_cannot_release`,
`evidence_immutable`, `exact_not_approximate`, `nan_rejected`, `missing_verifier_blocks`,
`underdetermination_reported`.

## Measured results

All 24 CI and all 120 seed cases pass their expected disposition. Across the 51 underlying fixture
cases: 51 accepted with correct answers, 51 rejected with wrong answers.

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

## Determinism

Cost is modelled from tool calls, not timed, so dispositions and deltas are byte-identical across
runs. Repeated executions of both manifests produce identical statuses and metrics. Reported
wall-clock time appears only in the smoke report and never in stored evidence.

## Provenance

Every case carries a `ProvenanceRef`: source `cognitive-os/sprint-20-fixtures`, Apache-2.0,
redistributable, authored for Sprint 20 and derived from no public benchmark set. There is no
contamination path from a published evaluation set, and no third-party benchmark material is
redistributed.
