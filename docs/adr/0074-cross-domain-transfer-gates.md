# ADR 0074: Transfer evidence, controls, and hard negative-transfer gates

## Status

Accepted for Sprint 20.

## Decision

A transfer claim is a measurement over named control arms, not a label. `TransferResult` requires
every member of `TransferArm` — source retention, target baseline, unchanged source revision,
minimally adapted, domain-specific, no-skill control, and unrelated domain — and rejects
construction if any is missing.

The transferred component is a real procedure: verification-driven repair turns "state an answer"
into "state an answer, let an independent checker judge it, and on failure recompute once and
re-verify". Arms differ only in whether that procedure is applied and where it came from. A
deterministic, seeded fault is injected into every third case so the procedure has something to
recover from, and all arms see identical faults on identical cases under identical budgets.

Hard gates are evaluated before the disposition and cannot be offset by target-domain quality:
source-domain retention loss, unrelated-domain loss, any increase in safety or policy violations,
and cost ratios beyond their declared ceilings. `TransferResult` refuses to hold
`positive_transfer` together with a non-empty `hard_gate_failures`, and migration `0012` repeats
that constraint in the database so no writer can record the combination.

Cost is modelled from the work performed — tool calls times a fixed unit — not measured from the
wall clock. A hard gate that reads a real clock is not reproducible: the same experiment flips
disposition on a busy machine. Wall-clock timing is an operational observation reported by
`scripts/domain_smoke_test.py` and is never stored as immutable evidence.

Thresholds are predeclared in `TransferThresholds` before the run. Post-hoc metric substitution is
a contract error, not a judgement call.

## Alternatives and consequences

Declaring transfer from a target-domain gain alone was rejected: it is exactly the failure the
gates exist to catch, and the negative-transfer fixture demonstrates the rejection. Measuring
latency from the clock was rejected after it made the disposition non-reproducible in practice.

The consequence is that the demonstrated transfer is narrow and honestly scoped. `TransferResult`
carries explicit limitations: the component is verification-driven repair rather than a general
skill, faults are injected rather than drawn from live traffic, and a single seeded run carries no
confidence interval.

## Verification

Measured on the Sprint 20 fixture set: target quality rises from 0.647 to 1.000 for the
mathematics-to-physics skill arm and from 0.625 to 1.000 for the mathematics-to-logic strategy arm,
with no source-domain or unrelated-domain regression and no hard gate breached. The
narrow-optimisation fixture is rejected on hard gates. Repeated runs return identical dispositions
and deltas.
