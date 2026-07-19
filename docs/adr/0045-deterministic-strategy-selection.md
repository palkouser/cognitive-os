# ADR 0045: Deterministic strategy selection

## Status

Accepted for Sprint 13.

## Decision

Selection first removes lifecycle, scope, sensitivity, capability, permission, and applicability
failures. Remaining candidates use ranking profile `strategy-ranking-v1`:

```text
score = specificity * 0.20
      + Wilson acceptance lower bound * 1.00
      + verifier quality * 0.25
      - repair rate * 0.15
      - latency ratio * 0.10
      - token ratio * 0.10
      - safety failure rate * 1.00
      - fallback rate * 0.20
```

Every input is deterministically quantized. Candidates below five outcomes are explicitly sparse.
Comparisons require ten compatible outcomes. A verified cold-start candidate can win only when no
measured verified alternative exists, regression evidence passes, policy allows it, and required
operator approval is present. The final tie-break is canonical strategy name then exact revision.

For example, an inapplicable candidate with a perfect history is excluded before ranking. Two
applicable unmeasured candidates with identical specificity sort by canonical identity. Provider
suggestions are recorded as advisory input but cannot affect applicability, weights, approval, or
the selected revision. Learned ranking and adaptive provider routing remain disabled.
