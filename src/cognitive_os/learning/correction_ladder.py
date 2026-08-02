"""S21D2-042: the deterministic baseline ladder the learned rung has to beat.

The baseline is the one number a caller could weaken to manufacture an apparent win, so it is
derived here from the ladder rather than accepted as an argument. `CorrectionEvaluatorManifest`
names the five rungs and the rule — `strongest_non_learned_rung_on_the_calibration_ladder` —
before any final outcome exists; this module runs them on the sealed calibration groups and
reports the strongest, whichever it turns out to be.

Every rung orders the four candidates of a task group using only what was available before the
sandbox ran, and the metric is the manifest's primary one: the fraction of task groups whose
first-ranked candidate the hidden verifier accepted. A rung that reads a label is not a weak
rung, it is a straw man pointing the other way, and `rank_with` refuses one by construction —
a rung function receives candidate features and the frozen order, and never a label.

One rung is structurally ineligible on this surface, and that is recorded rather than
substituted. `width_20_bounded_graph` is a *retrieval* arm: it shortlists twenty candidates
from a pool and reranks them by graph edit distance. A correction-ranking task presents exactly
four candidates, so a twenty-wide shortlist is the whole pool and the rung degenerates into its
own tie-break. §4.5 admits this by saying the graph rung counts "when it meets the resource
contract"; here it does not, and the honest report is an ineligible rung with its reason rather
than a fifth number produced by something else wearing its name.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow

FIXED_INPUT_ORDER = "fixed_input_order"
DETERMINISTIC_STATIC_ORDERING = "deterministic_static_ordering"
LEXICAL_SIMILARITY = "lexical_similarity"
FROZEN_MINILM_COSINE = "frozen_minilm_cosine"
WIDTH_20_BOUNDED_GRAPH = "width_20_bounded_graph"

#: The rung order `CorrectionEvaluatorManifest` froze. Kept as a tuple so the ladder cannot be
#: reordered into one where a different rung happens to come out strongest first.
LADDER_RUNGS: tuple[str, ...] = (
    FIXED_INPUT_ORDER,
    DETERMINISTIC_STATIC_ORDERING,
    LEXICAL_SIMILARITY,
    FROZEN_MINILM_COSINE,
    WIDTH_20_BOUNDED_GRAPH,
)

#: Why the graph rung cannot run on this surface. Stated once and reported verbatim.
GRAPH_RUNG_INELIGIBLE = (
    "a correction-ranking task presents exactly four candidates, so a twenty-wide shortlist is "
    "the entire pool and the rung reduces to its own tie-break; it meets no resource contract "
    "it does not already trivially satisfy"
)


@dataclass(frozen=True, slots=True)
class TaskGroupCandidates:
    """One task group's four candidates, in the frozen baseline order.

    The texts travel with the group because a baseline rung is not restricted to the fitted
    feature set — it is restricted to what was available before the sandbox ran, which the
    requirement and the candidate diff both are. Confining the ladder to the encoder's columns
    would weaken the baseline by accident, and the baseline is the one number that must not be
    weakened.
    """

    group: str
    ordered_candidate_ids: tuple[str, ...]
    rows: Mapping[str, FittedRow]
    requirement_text: str
    delta_texts: Mapping[str, str]

    def accepted(self, candidate_id: str) -> bool:
        return self.rows[candidate_id].accepted


#: A rung receives the group and returns an ordering. It never receives a label: the signature
#: is the straw-man guard, because a rung that cannot see the answer cannot be built to know it.
RungOrdering = Callable[[TaskGroupCandidates], tuple[str, ...]]


def _fixed_input_order(group: TaskGroupCandidates) -> tuple[str, ...]:
    """The sealed positional order. The floor, and the tie-break every other rung falls to."""
    return group.ordered_candidate_ids


def _static_ordering(group: TaskGroupCandidates) -> tuple[str, ...]:
    """Smallest edit first, by the pre-outcome counts, ties by the frozen order.

    A deterministic structural preference rather than a random one, and a defensible prior:
    the minimal repair is the one a careful author writes first.
    """
    position = {item: index for index, item in enumerate(group.ordered_candidate_ids)}
    names = ("added_line_count", "ast_node_count", "hunk_count")

    def key(candidate_id: str) -> tuple[float, ...]:
        vector = dict(group.rows[candidate_id].vector.values)
        return (*(vector[name] for name in names), position[candidate_id])

    return tuple(sorted(group.ordered_candidate_ids, key=key))


def _by_column(name: str) -> RungOrdering:
    """Order by one encoded column, descending, ties by the frozen order."""

    def ordering(group: TaskGroupCandidates) -> tuple[str, ...]:
        position = {item: index for index, item in enumerate(group.ordered_candidate_ids)}
        return tuple(
            sorted(
                group.ordered_candidate_ids,
                key=lambda candidate_id: (
                    -dict(group.rows[candidate_id].vector.values)[name],
                    position[candidate_id],
                ),
            )
        )

    return ordering


def _tokens(text: str) -> set[str]:
    """Lowercased alphanumeric runs. The same tokenisation the retrieval lexical arm uses."""
    return {token for token in re.split(r"[^0-9a-zA-Z]+", text.lower()) if token}


def _lexical(group: TaskGroupCandidates) -> tuple[str, ...]:
    """Jaccard overlap between the requirement and each candidate's diff, ties by frozen order.

    No index and no dependency, exactly like the retrieval arm of the same name, so the rung
    is the honest lexical baseline rather than a second embedding under another label.
    """
    wanted = _tokens(group.requirement_text)
    position = {item: index for index, item in enumerate(group.ordered_candidate_ids)}

    def overlap(candidate_id: str) -> float:
        tokens = _tokens(group.delta_texts[candidate_id])
        union = wanted | tokens
        return len(wanted & tokens) / len(union) if union else 0.0

    return tuple(
        sorted(
            group.ordered_candidate_ids,
            key=lambda candidate_id: (-overlap(candidate_id), position[candidate_id]),
        )
    )


_ELIGIBLE_RUNGS: dict[str, RungOrdering] = {
    FIXED_INPUT_ORDER: _fixed_input_order,
    DETERMINISTIC_STATIC_ORDERING: _static_ordering,
    LEXICAL_SIMILARITY: _lexical,
    FROZEN_MINILM_COSINE: _by_column("query_to_candidate_cosine"),
}


class LadderRung(HashedExperienceContract):
    """One rung's measured first-choice rate, or the reason it could not be measured."""

    name: NonEmptyStr
    kind: NonEmptyStr
    eligible: bool
    #: `None` exactly when the rung is ineligible. A rung that could not run has no score,
    #: and giving it zero would make an ineligible rung look like a beaten one.
    first_choice_rate: str | None = None
    groups_scored: int = Field(ge=0)
    ineligible_reason: str | None = None

    def model_post_init(self, context: object) -> None:
        if self.eligible and self.first_choice_rate is None:
            raise ValueError(f"{self.name} is eligible but recorded no score")
        if not self.eligible and self.first_choice_rate is not None:
            raise ValueError(f"{self.name} is ineligible and cannot carry a score")
        if not self.eligible and not self.ineligible_reason:
            raise ValueError(f"{self.name} is ineligible without saying why")


class CorrectionBaselineLadder(HashedExperienceContract):
    """The frozen ladder, and the strongest non-learned rung derived from it."""

    split: NonEmptyStr
    calibration_matrix_hash: Sha256Hex
    groups: int = Field(ge=1)
    rungs: tuple[LadderRung, ...] = Field(min_length=1)
    baseline_rule: NonEmptyStr = "strongest_non_learned_rung_on_the_calibration_ladder"
    strongest_non_learned_name: NonEmptyStr
    strongest_non_learned_rate: str
    created_at: UtcDatetime

    def model_post_init(self, context: object) -> None:
        eligible = [rung for rung in self.rungs if rung.eligible and rung.kind != "learned"]
        if not eligible:
            raise ValueError("a ladder with no eligible non-learned rung has no baseline")
        best = max(eligible, key=lambda rung: Decimal(str(rung.first_choice_rate)))
        if self.strongest_non_learned_name != best.name:
            raise ValueError(
                f"the ladder's strongest non-learned rung is {best.name!r}, but the record "
                f"names {self.strongest_non_learned_name!r}; the baseline is derived, never "
                "supplied"
            )
        if Decimal(self.strongest_non_learned_rate) != Decimal(str(best.first_choice_rate)):
            raise ValueError("the recorded baseline rate is not the strongest rung's rate")

    @property
    def baseline(self) -> Decimal:
        return Decimal(self.strongest_non_learned_rate)

    def rung(self, name: str) -> LadderRung:
        return next(item for item in self.rungs if item.name == name)


def group_candidates(
    matrix: FittedMatrix,
    *,
    order: Mapping[str, Sequence[str]],
    requirement_texts: Mapping[str, str],
    delta_texts: Mapping[str, str],
) -> tuple[TaskGroupCandidates, ...]:
    """Split a matrix into task groups, each carrying the frozen order the seal recorded."""
    by_group: dict[str, dict[str, FittedRow]] = {}
    for row in matrix.rows:
        by_group.setdefault(row.group, {})[str(row.candidate_id)] = row
    groups = []
    for name in sorted(by_group):
        ordered = tuple(order[name])
        if set(ordered) != set(by_group[name]):
            raise ValueError(f"group {name!r} was given an order for a different candidate set")
        groups.append(
            TaskGroupCandidates(
                group=name,
                ordered_candidate_ids=ordered,
                rows=by_group[name],
                requirement_text=requirement_texts[name],
                delta_texts={item: delta_texts[item] for item in ordered},
            )
        )
    return tuple(groups)


def first_choice_rate(groups: Sequence[TaskGroupCandidates], ordering: RungOrdering) -> Decimal:
    """The manifest's primary metric: how often the rung's first pick was accepted."""
    if not groups:
        raise ValueError("a rung cannot be scored on no groups")
    accepted = sum(1 for group in groups if group.accepted(ordering(group)[0]))
    return Decimal(accepted) / Decimal(len(groups))


def build_ladder(
    matrix: FittedMatrix,
    *,
    order: Mapping[str, Sequence[str]],
    requirement_texts: Mapping[str, str],
    delta_texts: Mapping[str, str],
    created_at: datetime,
    learned: Mapping[str, Decimal] | None = None,
) -> CorrectionBaselineLadder:
    """Run every eligible rung on the calibration groups and derive the baseline.

    `learned` carries any learned rung's already-measured rate. It is kept out of the baseline
    by `kind`, not by name, so a learned rung cannot become the baseline by being renamed.
    """
    groups = group_candidates(
        matrix,
        order=order,
        requirement_texts=requirement_texts,
        delta_texts=delta_texts,
    )
    rungs: list[LadderRung] = []
    for name in LADDER_RUNGS:
        ordering = _ELIGIBLE_RUNGS.get(name)
        if ordering is None:
            rungs.append(
                LadderRung(
                    name=name,
                    kind="deterministic",
                    eligible=False,
                    groups_scored=0,
                    ineligible_reason=GRAPH_RUNG_INELIGIBLE,
                )
            )
            continue
        rungs.append(
            LadderRung(
                name=name,
                kind="deterministic",
                eligible=True,
                first_choice_rate=str(first_choice_rate(groups, ordering)),
                groups_scored=len(groups),
            )
        )
    for name, rate in sorted((learned or {}).items()):
        rungs.append(
            LadderRung(
                name=name,
                kind="learned",
                eligible=True,
                first_choice_rate=str(rate),
                groups_scored=len(groups),
            )
        )

    eligible = [rung for rung in rungs if rung.eligible and rung.kind != "learned"]
    best = max(eligible, key=lambda rung: Decimal(str(rung.first_choice_rate)))
    return CorrectionBaselineLadder(
        split=matrix.split,
        calibration_matrix_hash=matrix.content_hash,
        groups=len(groups),
        rungs=tuple(rungs),
        strongest_non_learned_name=best.name,
        strongest_non_learned_rate=str(best.first_choice_rate),
        created_at=created_at,
    )
