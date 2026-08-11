"""Structural scans over the seven-channel relational representation, at the level it leaks.

W1's released scans prove separation where the v2 representation lives: no shared group, no
near-duplicate above the 0.999 floor, 400 distinct 390-channel vectors. The v3 relational
representation is seven numbers, and seven numbers alias: two candidates of two different
tasks — different canonical sources, different embeddings, different everything the v2 seal
records — can encode to the same seven values. The W2 pre-flight over the sealed D7 bytes
measured exactly that: eleven relational vectors appear in both the certification half and
the demoted bar-setting half, none of which shares a source, a group or a decision.

That distinction is the whole module. `corpus_roles` freezes "no fitted vector may appear in
both halves", and under the class D7 actually measures, the sentence's *leakage* reading and
its *literal* reading come apart:

*Leakage* — the thing the sentence exists to prevent — is a decision that helped place the
bar walking over it, or one candidate's bytes sitting in both halves. Its signatures are a
shared **decision** (the four relational vectors in slot order) or a shared **canonical
source**. Either is a hard failure here.

*Aliasing* is two different sources encoding identically in a low-entropy code. It is a
property of the representation, not of the corpus split; it cannot move a bar in favour of a
certified decision, because the certified decision's own margin is computed from its own
group's four vectors whatever any other task's candidate encoded to. It is reported with its
counts, never silently passed.

The scan proves the first kind absent and quantifies the second, per half and across every
half pair, so the record W2 seals states the true disjointness properties of the
representation it measures rather than carrying a v2-era sentence the v3 bytes falsify.

Label-free and score-free by construction: the scan reads sealed vectors and canonical
source hashes, never an outcome, a label, a margin or an ordering — safe to run over an
unread certification half, the same category as W1's own snapshot scans.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.experience import HashedExperienceContract

#: One rounding rule for vector identity, stated once. Twelve decimal places is finer than
#: any channel's real precision (the scalars are clip-scaled to [0, 1], the share is a ratio
#: of small integers) and coarse enough to be stable across a serialisation round trip.
RELATIONAL_KEY_DECIMALS = 12


def relational_key(numbers: Sequence[float]) -> tuple[float, ...]:
    """The identity of one relational vector, under the module's single rounding rule."""
    return tuple(round(value, RELATIONAL_KEY_DECIMALS) for value in numbers)


def decision_signature(
    order: Sequence[str], numbers: Mapping[str, Sequence[float]]
) -> tuple[tuple[float, ...], ...]:
    """The identity of one ranking decision: the four relational vectors in slot order."""
    return tuple(relational_key(numbers[candidate_id]) for candidate_id in order)


class RelationalHalfProfile(HashedExperienceContract):
    """One half's structure under the relational representation."""

    half: NonEmptyStr
    groups: int = Field(ge=1)
    candidate_vectors: int = Field(ge=1)
    distinct_vectors: int = Field(ge=1)
    #: Distinct four-vector signatures — the independent-decision count §2.3's first
    #: condition reads. A duplicate here is one decision counted twice.
    independent_decision_signatures: int = Field(ge=1)
    #: Groups carrying at least one within-group duplicate vector. Such a pair is a tie the
    #: frozen order breaks; a tie at the top of a group is a zero margin no positive bar
    #: admits, so these groups bound the reachable coverage from above.
    groups_with_within_group_aliasing: tuple[NonEmptyStr, ...] = ()


class RelationalPairScan(HashedExperienceContract):
    """Two halves compared at the two levels that leak and the one that merely aliases."""

    first_half: NonEmptyStr
    second_half: NonEmptyStr
    #: The leakage signatures. Either being non-zero is a hard failure.
    shared_decision_signatures: int = Field(ge=0)
    shared_canonical_sources: int = Field(ge=0)
    #: The aliasing count: relational vectors present in both halves whose underlying
    #: canonical sources all differ. Reported, never failed on.
    aliased_vectors: int = Field(ge=0)
    first_half_groups_touched_by_aliasing: tuple[NonEmptyStr, ...] = ()

    @property
    def leaks(self) -> bool:
        return bool(self.shared_decision_signatures or self.shared_canonical_sources)


class RelationalSeparationScanV1(HashedExperienceContract):
    """The whole scan: every half profiled, every pair compared, one verdict field.

    `clean` is derived from the pair scans and refuses to be stated independently: the scan
    is clean exactly when no pair leaks. Aliasing does not dirty it — the reading lives in
    the module docstring and in `aliasing_reading`, which travels in the sealed bytes.
    """

    revision: int = 1
    halves: tuple[RelationalHalfProfile, ...] = Field(min_length=2)
    pairs: tuple[RelationalPairScan, ...] = Field(min_length=1)
    clean: bool
    aliasing_reading: NonEmptyStr = (
        "an aliased vector is two different canonical sources encoding identically in a "
        "seven-channel code; it shares no decision, no group and no bytes across the "
        "halves, and a certified decision's margin is computed from its own group's four "
        "vectors whatever any other task's candidate encoded to"
    )

    def model_post_init(self, context: object) -> None:
        derived = not any(pair.leaks for pair in self.pairs)
        if self.clean != derived:
            raise ValueError(
                "`clean` is derived from the pair scans; a record stating it independently "
                "could call a leaking split clean"
            )


def profile_half(
    half: str,
    groups: Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]],
) -> RelationalHalfProfile:
    """Profile one half: `groups` maps a group name to its (slot order, vectors)."""
    distinct: set[tuple[float, ...]] = set()
    signatures: set[tuple[tuple[float, ...], ...]] = set()
    aliased_groups: list[str] = []
    candidates = 0
    for name in sorted(groups):
        order, numbers = groups[name]
        keys = [relational_key(numbers[candidate_id]) for candidate_id in order]
        candidates += len(keys)
        distinct.update(keys)
        signatures.add(tuple(keys))
        if len(set(keys)) < len(keys):
            aliased_groups.append(name)
    return RelationalHalfProfile(
        half=half,
        groups=len(groups),
        candidate_vectors=candidates,
        distinct_vectors=len(distinct),
        independent_decision_signatures=len(signatures),
        groups_with_within_group_aliasing=tuple(aliased_groups),
    )


def scan_half_pair(
    first: tuple[str, Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]]],
    second: tuple[str, Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]]],
    *,
    canonical_source_hashes: Mapping[str, str],
) -> RelationalPairScan:
    """Compare two halves. `canonical_source_hashes` maps candidate id to the sealed v2
    canonical source hash — the authority that separates aliasing from a shared source."""
    first_name, first_groups = first
    second_name, second_groups = second

    def vectors_of(
        groups: Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]],
    ) -> dict[tuple[float, ...], set[str]]:
        by_key: dict[tuple[float, ...], set[str]] = {}
        for _, (order, numbers) in groups.items():
            for candidate_id in order:
                by_key.setdefault(relational_key(numbers[candidate_id]), set()).add(candidate_id)
        return by_key

    def signatures_of(
        groups: Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]],
    ) -> set[tuple[tuple[float, ...], ...]]:
        return {decision_signature(order, numbers) for _, (order, numbers) in groups.items()}

    first_vectors = vectors_of(first_groups)
    second_vectors = vectors_of(second_groups)
    shared_keys = set(first_vectors) & set(second_vectors)

    shared_sources = 0
    for key in shared_keys:
        first_sources = {canonical_source_hashes[item] for item in first_vectors[key]}
        second_sources = {canonical_source_hashes[item] for item in second_vectors[key]}
        shared_sources += len(first_sources & second_sources)

    touched = tuple(
        sorted(
            name
            for name, (order, numbers) in first_groups.items()
            if any(relational_key(numbers[candidate_id]) in shared_keys for candidate_id in order)
        )
    )
    return RelationalPairScan(
        first_half=first_name,
        second_half=second_name,
        shared_decision_signatures=len(signatures_of(first_groups) & signatures_of(second_groups)),
        shared_canonical_sources=shared_sources,
        aliased_vectors=len(shared_keys) - shared_sources,
        first_half_groups_touched_by_aliasing=touched,
    )


def scan_relational_separation(
    halves: Mapping[str, Mapping[str, tuple[Sequence[str], Mapping[str, Sequence[float]]]]],
    *,
    canonical_source_hashes: Mapping[str, str],
) -> RelationalSeparationScanV1:
    """Profile every half and compare every pair, in sorted-name order."""
    names = sorted(halves)
    if len(names) < 2:
        raise ValueError("a separation scan over one half separates nothing")
    profiles = tuple(profile_half(name, halves[name]) for name in names)
    pairs = tuple(
        scan_half_pair(
            (first, halves[first]),
            (second, halves[second]),
            canonical_source_hashes=canonical_source_hashes,
        )
        for index, first in enumerate(names)
        for second in names[index + 1 :]
    )
    return RelationalSeparationScanV1(
        halves=profiles,
        pairs=pairs,
        clean=not any(pair.leaks for pair in pairs),
    )
