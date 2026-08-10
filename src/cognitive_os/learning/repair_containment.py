"""Repair containment — the within-group relational signal the fitted classes never read.

Sprint 21D6 ended on `leak_budget_exceeded`, and its §4 measurement (run read-only over the
released D5 and D6 bytes) decided the successor question: the learned-minus-baseline
difference collapses across authoring runs — +0.46 on D5's calibration corpus, +0.14 on D6's
certification corpus, against a `fixed_input_order` rung that sits at 0.42 on both — so the
sealed direction does not transfer, and per the D7 handoff's own §4 rule the class question
is the right one. This module is the class question's first half: the signal.

**What the corpus contract guarantees, the representation never used.** Every certification
group is authored to the same anatomy: the baseline fails the hidden suite, variants one and
two repair the contract by materially different routes, variants three and four each fix one
edge case only. A complete repair therefore tends to *contain* each partial repair's change,
and a partial repair contains neither its sibling nor a complete one. That relation is the
question the hidden verifier actually asks — does this candidate cover both described edge
cases — and it is computable before the sandbox runs, from nothing but the task package: the
baseline module and the four candidate sources.

`repair_containment_share(c)` is the mean, over the other candidates `d` whose repair adds at
least one line, of `|added(d) ∩ added(c)| / |added(d)|`, where `added(x)` is the set of
stripped non-empty lines in `x` that are not in the baseline. A candidate that subsumes the
group's other proposed changes scores near one; a candidate carrying only its own partial
change scores low.

**Why this survives the six frozen invariance cases when a requirement overlap does not.**
`transformations_d3` renames identifiers with *one* map applied to every source in the group —
baseline, all four variants, both suites — and rewrites only the issue text. A consistent
rename is a bijection on tokens, hence a bijection on stripped lines, so every intersection
and every set size above is preserved exactly and the containment ordering cannot move. An
issue rewrite touches no source at all. Contrast the v1 encoder's `query_to_candidate_cosine`,
removed at v2 precisely because one side of that relation moves alone under a rename: any
channel relating a candidate to the *requirement text* fails the transform that renames only
the sources. The rule this module encodes: within-group source-to-source relations are
invariant; source-to-requirement relations are not, and none is computed here.

**What this signal is not.** It reads no label, no verifier output and no outcome — only
sources published to the solver before execution. It is corpus-contract-aware: its power
comes from the two-complete-two-partial anatomy the authoring contract froze, and on a group
without that anatomy it degrades to a consensus-coverage prior — how much of the group's
proposed change this candidate subsumes — rather than failing. Where every candidate adds
nothing (a pure-deletion group), every share is zero and ranking falls back to the caller's
tie-break, which is the frozen baseline order everywhere in this programme.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

#: The channel name the successor representation carries this signal under.
REPAIR_CONTAINMENT_CHANNEL = "repair_containment_share"


def repair_lines(source: str) -> frozenset[str]:
    """The stripped non-empty lines of one module source."""
    return frozenset(line.strip() for line in source.splitlines() if line.strip())


def added_lines(baseline_source: str, candidate_source: str) -> frozenset[str]:
    """The candidate's repair, as the set of its lines the baseline does not contain."""
    return repair_lines(candidate_source) - repair_lines(baseline_source)


def containment_shares(
    baseline_source: str,
    sources_by_candidate: Mapping[str, str],
) -> dict[str, float]:
    """Every candidate's repair-containment share against the rest of its group.

    Deterministic in its inputs and nothing else: no corpus statistic, no fitted bound and
    no randomness enters, so the channel needs no clip-and-scale envelope — it lives in
    [0, 1] by construction and two corpora are comparable on it without sharing anything.
    """
    if len(sources_by_candidate) < 2:
        raise ValueError("a containment share needs at least two candidates to relate")
    added = {
        candidate_id: added_lines(baseline_source, source)
        for candidate_id, source in sources_by_candidate.items()
    }
    shares: dict[str, float] = {}
    for candidate_id in sources_by_candidate:
        parts = [
            len(added[other] & added[candidate_id]) / len(added[other])
            for other in sources_by_candidate
            if other != candidate_id and added[other]
        ]
        shares[candidate_id] = sum(parts) / len(parts) if parts else 0.0
    return shares


def containment_ordering(
    baseline_source: str,
    sources_by_candidate: Mapping[str, str],
    *,
    baseline_order: Sequence[str],
) -> tuple[str, ...]:
    """The candidates by descending containment share, ties on the frozen baseline order.

    Exposed so the signal can be measured as a deterministic ordering in its own right —
    a rung has to be reportable alone before a class is allowed to lean on it, and the gate
    owner may want it on the ladder, which would raise the baseline every learned candidate
    must beat rather than lower it.
    """
    if set(baseline_order) != set(sources_by_candidate):
        raise ValueError("the baseline order and the candidate set disagree")
    shares = containment_shares(baseline_source, sources_by_candidate)
    position = {candidate_id: index for index, candidate_id in enumerate(baseline_order)}
    return tuple(sorted(baseline_order, key=lambda item: (-shares[item], position[item])))
