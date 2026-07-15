# ADR 0036: Bitemporal semantic claims

- Status: Accepted
- Date: 2026-07-15

## Context

Evidence can arrive after the domain fact it describes, and a later correction must not alter what
Cognitive OS previously knew. A claim therefore needs both domain validity and recorded history.

## Decision

A stable claim identity is `(scope, canonical subject, predicate)` and each immutable revision owns
its object, statement, belief status, confidence, reason, evidence snapshot, `valid_from`, optional
`valid_to`, and `recorded_at`. Valid intervals are UTC half-open `[valid_from, valid_to)`. The system
time of a revision is its immutable `recorded_at`.

`valid_at` selects revisions whose valid interval contains the instant. `known_at` excludes revisions
recorded later than the instant. When combined, both filters apply before the greatest eligible
revision is selected. Current queries exclude retracted and superseded state by default.

Future validity is retained without hiding the earlier interval. Backdated evidence is recorded at
its actual later system time and cannot leak into an earlier `known_at` view. Supersession and
retraction append revisions; they never update history. Overlapping values remain visible and may
open a contradiction.

Example: Python 3.12 is valid from 2026-07-01 and recorded on 2026-07-15. Python 3.13 is valid from
2027-01-10 and recorded on 2027-01-11. A `known_at=2027-01-05` query cannot return the second
revision. A retraction recorded on 2027-02-01 does not change a `known_at=2027-01-20` result.

## Alternatives considered

- One mutable current fact: rejected because it destroys audit and historical knowledge views.
- Valid time only: rejected because late evidence leaks into earlier system knowledge.
- Destructive interval correction: rejected because prior decisions must remain reproducible.

## Consequences

Queries and indexes must cover both clocks. Conflicting overlaps are stored rather than erased.
Revision continuity and future-revision leakage are mandatory tests.
