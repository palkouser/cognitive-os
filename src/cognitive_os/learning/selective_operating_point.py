"""S21D4-021: the zero-error operating point, derived once, from calibration only.

D3 asked the grid for a setting that made no confident error anywhere and also answered almost
everywhere, and the grid had no such point. That is not surprising: a selective ranker buys
precision with coverage, and D3's contract forbade the purchase. Revision 4 makes the purchase
explicit — pick the confidence at which the answered decisions are all correct, then report what
that costs in coverage, and report how little zero errors on a small sample actually proves.

Three refusals live here, and each of them exists because the alternative is a threshold that
chose itself after seeing what it needed to beat:

*Calibration only.* A threshold derived from final, promotion or metamorphic decisions is a
threshold fitted to the holdout. `derive_zero_error_point` refuses any other split by name.

*One derivation.* Deriving twice and keeping the better one is a search, not a pre-registration.
A second call must reproduce the first exactly; `derivation_hash` is what "exactly" means, and
it deliberately excludes the wall clock so that reproducing after a restart is possible at all.

*Independent decisions only.* The scored set is censused before it is sorted, and replicas are
refused rather than silently deduplicated: a caller holding six copies of one decision has a
counting bug, and dropping five of them quietly would hide it.

The rule itself is a sorted quantile and nothing more. No model, no fit, no dependency, no new
fitted channel — the score is the released bounded k-NN confidence, unchanged.

    threshold = the highest score among answered decisions that are wrong
    admitted   = answered decisions scoring strictly above the threshold

Revision 4 originally said "the highest threshold at which every answered decision above it is
correct", which names no point: the thresholds satisfying that condition are an upward-closed
set, so every larger one satisfies it too, up to the one that admits nothing at all. Amendment 1
replaces the word before any threshold was derived and before the calibration set was resolved —
see `evidence/sprint-21d4-contracts-amendment-1.json`, which is bound to the unchanged hash of
the sealed original. `AMENDED_DERIVATION_STEP` below is the operative sentence, and the amendment
record carries its digest so the contract and this module cannot drift apart.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import (
    INDEPENDENT_DENOMINATOR,
    DecisionCensusV4,
)

#: The only split a threshold may be derived from.
CALIBRATION_SPLIT = "calibration"

#: The sentence S21D4-011 froze, kept verbatim so the amendment can name what it replaced.
SEALED_DERIVATION_STEP = (
    "the zero-error point is the highest threshold at which every answered decision above it is "
    "correct"
)

#: Amendment 1's replacement. It names one point instead of an unbounded family of them.
AMENDED_DERIVATION_STEP = (
    "the zero-error point is the lowest threshold at which every answered decision strictly "
    "above it is correct, equivalently the highest score among answered decisions that are "
    "wrong; it is the boundary of the zero-error region and the only member of it whose "
    "coverage is worth reporting, because every higher threshold admits a strict subset"
)

DERIVATION_RULE = (
    "score every independent clean calibration decision with the released bounded k-NN "
    f"confidence; sort the answered ones by score descending; {AMENDED_DERIVATION_STEP}; admit "
    "the answered decisions scoring strictly above it; report coverage over independent "
    "decisions and the Clopper-Pearson one-sided 95% upper bound on the true error rate"
)

DERIVATION_READING = (
    "amendment 1: the sealed wording said 'highest', which names no point, because the "
    "thresholds admitting only correct decisions are upward-closed and the largest of them "
    "admits nothing. The operative rule takes the boundary of that set"
)


class OperatingPointError(ValueError):
    """A threshold was asked for from the wrong evidence, or asked for twice."""


def zero_error_upper_bound(n: int, alpha: float = 0.05) -> float:
    """The Clopper-Pearson one-sided upper bound on the error rate after zero errors in `n`.

    Zero errors is not evidence of a zero rate, it is evidence of a rate below this. At twenty
    decisions the bound is 13.9%; the whole reason D4 authors a hundred is that this number
    falls only as fast as the sample grows.
    """
    if n <= 0:
        raise ValueError("a bound over zero decisions bounds nothing")
    return float(1.0 - alpha ** (1.0 / n))


@dataclass(frozen=True, slots=True)
class ScoredDecision:
    """One scored ranking decision, as the caller measured it before any threshold existed."""

    decision_id: str
    #: The fitted feature vector's hash. Two decisions sharing one are one decision.
    feature_hash: str
    score: Decimal
    answered: bool
    correct: bool


class OperatingPointV4(HashedExperienceContract):
    """A derived threshold, everything it was derived from, and what it costs."""

    revision: int = 4
    split: NonEmptyStr = CALIBRATION_SPLIT
    calibration_source_hash: Sha256Hex
    census: DecisionCensusV4
    derivation_rule: NonEmptyStr = DERIVATION_RULE
    derivation_reading: NonEmptyStr = DERIVATION_READING
    rate_denominator: NonEmptyStr = INDEPENDENT_DENOMINATOR

    zero_error_point_exists: bool
    #: `None` when no threshold admits anything — every answered decision was wrong, or none was
    #: answered at all. A null is the honest record; a threshold above every score is not.
    threshold: str | None = None
    admitted_decisions: int = Field(default=0, ge=0)
    errors_above_threshold: int = Field(default=0, ge=0)
    coverage: str | None = None
    zero_error_upper_bound_95: str | None = None

    #: The identity a second derivation must reproduce. Excludes the wall clock on purpose.
    derivation_hash: Sha256Hex
    derived_at: UtcDatetime

    #: These raise plain `ValueError`, not `OperatingPointError`: pydantic wraps whatever a
    #: validator raises into a `ValidationError`, so the subclass would be invisible to a caller
    #: anyway. `OperatingPointError` is reserved for the derivation function, where a caller can
    #: actually catch it.
    @model_validator(mode="after")
    def a_derived_point_is_zero_error_or_it_is_not_a_point(self) -> OperatingPointV4:
        if self.split != CALIBRATION_SPLIT:
            raise ValueError(f"a threshold derived from {self.split!r} is fitted to a holdout")
        if self.errors_above_threshold:
            raise ValueError("a zero-error operating point admits no error")
        present = (self.threshold, self.coverage, self.zero_error_upper_bound_95)
        if self.zero_error_point_exists:
            if any(item is None for item in present) or not self.admitted_decisions:
                raise ValueError(
                    "an existing operating point names its threshold, coverage and bound"
                )
        elif any(item is not None for item in present) or self.admitted_decisions:
            raise ValueError("a point that does not exist admits nothing")
        return self


def derive_zero_error_point(
    decisions: Sequence[ScoredDecision],
    *,
    split: str,
    calibration_source_hash: str,
    derived_at: datetime,
    previous: OperatingPointV4 | None = None,
) -> OperatingPointV4:
    """Derive the point once, from calibration, over independent decisions only.

    `previous` is how the single-shot rule is enforced across a process restart: a caller that
    already holds a derivation passes it back, and a second derivation that does not reproduce it
    is refused. Reproducing it is allowed, and is exactly the determinism proof.
    """
    if split != CALIBRATION_SPLIT:
        raise OperatingPointError(
            f"the operating point is derived from the {CALIBRATION_SPLIT} split only; "
            f"{split!r} is final, promotion or metamorphic evidence"
        )
    census = DecisionCensusV4.from_feature_hashes([item.feature_hash for item in decisions])
    if census.replicated_decisions:
        raise OperatingPointError(
            f"{census.replicated_decisions} of {census.nominal_decisions} scored decisions "
            "repeat another's fitted vector; a threshold over replicas is a threshold over one "
            "decision counted many times"
        )

    answered = sorted(
        (item for item in decisions if item.answered),
        key=lambda item: (-item.score, item.decision_id),
    )
    wrong = [item.score for item in answered if not item.correct]
    threshold = max(wrong) if wrong else None
    admitted = [item for item in answered if threshold is None or item.score > threshold]

    exists = bool(admitted)
    coverage = (
        Decimal(len(admitted)) / Decimal(census.independent_decisions)
        if exists and census.independent_decisions
        else None
    )
    bound = round(zero_error_upper_bound(len(admitted)), 6) if exists else None

    body = {
        "split": split,
        "calibration_source_hash": calibration_source_hash,
        "rule": DERIVATION_RULE,
        "nominal_decisions": census.nominal_decisions,
        "independent_decisions": census.independent_decisions,
        "threshold": str(threshold) if exists else None,
        "admitted_decisions": len(admitted),
        "coverage": str(coverage) if coverage is not None else None,
        "zero_error_upper_bound_95": str(bound) if bound is not None else None,
    }
    derivation_hash = sha256(
        "\n".join(f"{key}={body[key]}" for key in sorted(body)).encode()
    ).hexdigest()

    point = OperatingPointV4(
        split=split,
        calibration_source_hash=calibration_source_hash,
        census=census,
        zero_error_point_exists=exists,
        threshold=str(threshold) if exists else None,
        admitted_decisions=len(admitted),
        coverage=str(coverage) if coverage is not None else None,
        zero_error_upper_bound_95=str(bound) if bound is not None else None,
        derivation_hash=derivation_hash,
        derived_at=derived_at,
    )
    if previous is not None and previous.derivation_hash != point.derivation_hash:
        raise OperatingPointError(
            "a second, different operating point was derived from the same calibration split; "
            f"the sealed derivation is {previous.derivation_hash}, this one is "
            f"{point.derivation_hash}"
        )
    return point
