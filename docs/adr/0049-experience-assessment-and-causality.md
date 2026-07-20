# ADR 0049: Experience assessment and causality

## Status

Accepted for Sprint 14.

## Decision

Step status comes from authoritative events. Correctness evidence is prioritized as acceptance,
required verifier, deterministic policy, tool postcondition, explicit correction, then provider
proposal. Necessity and efficiency use versioned deterministic signals and may remain `unknown`.

The compiler distinguishes the first policy violation, invalid evidence, objective verifier
failure, incorrect tool postcondition, corrected provider proposal, inefficient step, and unknown
causal origin. The first observed failure is not automatically its cause. A provider assertion is
never causal evidence.

Contribution labels are limited to `helpful`, `neutral`, `harmful`, and `unknown`. Every label has
exact evidence and a causal-strength marker. A successful repair may correlate with a correction;
one trajectory cannot establish component or model superiority. Ambiguous, failed, cancelled, and
repaired examples preserve their limitations.

## Rejected alternatives

Numeric causal scores, provider self-attribution, learned attribution, and forced classifications
were rejected because Sprint 14 has no causal experiment or adequate comparison cohort.
