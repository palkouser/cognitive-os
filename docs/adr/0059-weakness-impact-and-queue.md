# ADR 0059: Weakness impact and queue policy

## Status

Accepted for Sprint 17.

## Decision

Impact uses 13 versioned deterministic dimensions: frequency, affected tasks, severity, safety,
correctness, user corrections, cost, latency, repair iterations, recency, reproducibility, evidence
confidence, and strategic reach. Decimal normalization, explicit missing values, uncertainty, and
fixed weights make every score replayable. Safety and correctness floors prevent dilution.

A frequent low-impact issue may score above an informational item but remains below safety floors.
A single rare critical sandbox failure receives the critical floor while still requiring explicit
operator approval for confirmation. Queue order is priority, blocker state, then weakness UUID.
Entries contain evidence-backed next-analysis actions, never repair recommendations or destination
writes. No learned scoring is used.

## Rejected alternatives

Learned ranking, adaptive weights, provider priority, frequency-only scoring, and repair execution
from queue entries are rejected.
