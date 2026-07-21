# ADR 0054: Deterministic capability estimation

## Status

Accepted for Sprint 16.

## Decision

Binary dimensions use reproducible Wilson intervals. Continuous dimensions retain sample count,
mean or median, missing count, and deterministic `Decimal` quantization. Source classes remain
separate. Cohort lookup follows exact-to-global fallback, and broader or low-sample cohorts increase
an explicit uncertainty penalty. Full rebuilds derive solely from immutable observations.

## Rejected alternatives

Learned estimators, silent global averages, unknown-as-zero conversion, provider confidence, and
mandatory statistical libraries are rejected.
