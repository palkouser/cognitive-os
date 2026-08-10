"""S21D5's typed stop, answered in code: split-conformal admission over the sealed margin.

D5 stopped at §3.3 step 5, `selective_margin_bound`, and the stop names the defect precisely:
the direction ranks — 0.91 and 0.88 first-choice against a 0.42 baseline — and the zero-error
prefix rule certifies 0.26 and 0.27 of it against a 0.40 floor. The prefix rule walks the margin
ordering down to the first wrong decision and stops, so one badly-placed error truncates
everything below it: at 720 rows the ordering would admit 50 decisions at the cost of a single
error, and the rule stops at 27 because the 28th is wrong. A rule whose coverage is decided by
the position of one error is a rule with variance, not a bound.

This module is the one thing the D6 pre-registration changes: the map from a ranked group to an
admit/abstain decision. Everything upstream — the v2 encoder, the alpha-normaliser, the
`pairwise-contrastive-linear-v1` class, the two sealed directions — is kept, unchanged and
unrefitted, because refitting the direction would confound the one thing the sprint is varying.

The rule is split conformal and nothing more. Hold out a conformal half of the calibration
groups, take the margins of the answered decisions the ranker got wrong there, and set the bar
at the finite-sample (1-alpha) quantile of that distribution:

    m          = wrong answered decisions in the conformal half
    rank       = ceil((1-alpha) * (m+1))
    threshold  = the rank-th smallest wrong margin, when rank ≤ m
    admitted   = certification decisions scoring strictly above the threshold

What that buys is a coverage that degrades smoothly with alpha rather than being hostage to one
point. What it costs is that zero is no longer on the menu: the record states an error budget
and a Clopper—Pearson upper bound on the realised rate, never a claimed zero.

**Alpha bounds the leak, not the precision.** The quantile is taken over the margins of *errors*,
so what it guarantees is P(admitted | wrong) <= alpha — the share of the ranker's mistakes that
reach the caller. The share of admitted decisions that are wrong is a different number, smaller
by roughly the error rate over the coverage, and it is the one §2.3 reads; this module measures
it on the certification half and bounds it, rather than claiming it. Reading alpha as the second
number is the mistake this paragraph exists to prevent. Whether a stated
bound at a pre-registered alpha is an acceptable reading of §2.3's "exactly zero confident errors"
is a *contract* question, answered in the successor's pre-registration before any margin is
read — which is why `derive_conformal_point` refuses to run without the sealed record's hash.
Do not run split-conformal and then argue that its alpha is what zero always meant.

Four refusals live here, each because the alternative is a bar that chose itself after seeing
what it needed to beat:

*Calibration only.* A threshold derived from final, promotion or metamorphic decisions is a
threshold fitted to the holdout. Same refusal, same name, as the zero-error rule it replaces.

*Alpha before margins.* alpha arrives with the hash of the pre-registration that named it, both go
into the derivation hash, and the single-derivation `previous=` rule refuses a second, different
derivation from the same calibration source. Trying a second alpha is a search, not a derivation.

*Disjoint halves.* The half that sets the bar and the half that is measured against it must
share no fitted vector. A decision that helped place the threshold and then walked over it
would be certifying itself.

*Independent decisions only.* Both halves are censused before anything is sorted, and replicas
are refused rather than deduplicated, exactly as in `selective_operating_point`.

Two honesty clauses the zero-error rule never needed:

*No errors is no quantile.* When the conformal half contains no wrong decision, the wrong-margin
distribution does not exist and neither does its quantile. The record says so with a typed null
— it does not admit everything, the way `every_answered_decision_was_correct` let the prefix
rule do, because "no error was seen in the other half" is not a bar.

*Too few errors is no quantile either.* The finite-sample rank can exceed the sample: at alpha=0.05
five wrong margins are asked for their 6th smallest. The record keeps the rank it computed so a
reader can see exactly why the quantile does not exist.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from hashlib import sha256
from math import comb

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import (
    INDEPENDENT_DENOMINATOR,
    DecisionCensusV4,
)
from cognitive_os.learning.selective_operating_point import (
    CALIBRATION_SPLIT,
    ScoredDecision,
)

DERIVATION_RULE = (
    "score every independent clean calibration decision with the sealed pairwise-contrastive "
    "margin; split the calibration groups into a conformal half and a certification half with "
    "no shared fitted vector; take the margins of the answered decisions the ranker got wrong "
    "in the conformal half, sort them ascending, and set the threshold to the "
    "ceil((1-alpha)*(m+1))-th smallest of the m wrong margins; admit the certification "
    "decisions scoring strictly above it; report coverage over independent certification "
    "decisions, the errors among admitted decisions, and the Clopper-Pearson one-sided 95% "
    "upper bound on the true error rate among admitted decisions"
)

DERIVATION_READING = (
    "split conformal replaces the zero-error prefix: the bar is a quantile of the wrong "
    "decisions' margin distribution rather than the position of the single highest-scoring "
    "error, so coverage degrades smoothly with alpha instead of being hostage to one point; "
    "what it buys costs the zero — the record states an error budget and a bound, never a "
    "claimed zero rate. Alpha bounds the leak rate P(admitted | the decision is wrong), not "
    "the error rate among admitted decisions: the bar is a quantile of the margins of errors, "
    "so a fresh error clears it with probability at most alpha. The second quantity is the one "
    "§2.3 cares about, it is roughly the first times the error rate over the coverage, and it "
    "is measured on the certification half rather than guaranteed here — errors_admitted "
    "counts it and error_upper_bound_95 bounds it. Both readings hold only if the two halves "
    "are exchangeable, which is a claim about how the corpus was authored and not something "
    "this module can check"
)


class ConformalPointError(ValueError):
    """A bar was asked for from the wrong evidence, the wrong alpha, or asked for twice."""


def admitted_error_upper_bound(errors: int, admitted: int) -> float:
    """The Clopper-Pearson one-sided 95% upper bound on the error rate after `errors` in
    `admitted`.

    The `errors == 0` case reproduces `zero_error_upper_bound` exactly — the zero-error rule's
    bound is this one at k = 0 — so the two rules' claims stay on one scale. `errors` observed
    is not evidence of that rate; it is evidence of a rate below this.

    The 95% is not a parameter. The contract field is named `error_upper_bound_95`, so a caller
    passing another significance would store a 90% bound under a name claiming 95, and the whole
    point of these records is that a reader can trust the name. Bisection because an exact beta
    quantile needs scipy, which is an optional extra here rather than a runtime dependency; it
    agrees with a 200-iteration run bit for bit, and `errors == admitted` needs no branch because
    the CDF is then 1 everywhere and the loop already returns 1.0.

    The bound reads the admitted decisions as a fixed-size sample, which is the same reading D4
    and D5 stored: the admitted set is selected by margin, so this is the established convention
    rather than an exact conditional statement.
    """
    if admitted <= 0:
        raise ValueError("a bound over zero admitted decisions bounds nothing")
    if not 0 <= errors <= admitted:
        raise ValueError("errors must lie between zero and the admitted count")

    def binomial_cdf(p: float) -> float:
        return sum(comb(admitted, k) * p**k * (1 - p) ** (admitted - k) for k in range(errors + 1))

    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        if binomial_cdf(mid) > 0.05:
            low = mid
        else:
            high = mid
    return high


def conformal_rank(alpha: Decimal, wrong_count: int) -> int:
    """The finite-sample quantile rank: ceil((1-alpha) * (m+1)), always at least one."""
    return int(((1 - alpha) * (wrong_count + 1)).to_integral_value(rounding=ROUND_CEILING))


class ConformalOperatingPointV5(HashedExperienceContract):
    """A conformal bar, everything it was derived from, and the error budget it states."""

    revision: int = 5
    split: NonEmptyStr = CALIBRATION_SPLIT
    calibration_source_hash: Sha256Hex
    #: The sealed pre-registration that named alpha before any margin was read. The derivation
    #: refuses to run without it; a bar without one is a bar chosen after the fact.
    preregistration_hash: Sha256Hex
    alpha: NonEmptyStr
    conformal_census: DecisionCensusV4
    certification_census: DecisionCensusV4
    derivation_rule: NonEmptyStr = DERIVATION_RULE
    derivation_reading: NonEmptyStr = DERIVATION_READING
    rate_denominator: NonEmptyStr = INDEPENDENT_DENOMINATOR

    wrong_decisions_in_conformal_split: int = Field(ge=0)
    #: Recorded even when it exceeds the sample, so the stored bytes show *why* no quantile
    #: exists rather than only that none does.
    quantile_rank: int = Field(ge=1)
    quantile_exists: bool
    threshold: str | None = None

    admitted_decisions: int = Field(default=0, ge=0)
    errors_admitted: int = Field(default=0, ge=0)
    coverage: str | None = None
    observed_error_rate: str | None = None
    error_upper_bound_95: str | None = None

    #: The identity a second derivation must reproduce. Excludes the wall clock on purpose.
    derivation_hash: Sha256Hex
    derived_at: UtcDatetime

    @model_validator(mode="after")
    def a_stored_bar_must_still_be_the_bar_the_rule_names(
        self,
    ) -> ConformalOperatingPointV5:
        if self.split != CALIBRATION_SPLIT:
            raise ValueError(f"a threshold derived from {self.split!r} is fitted to a holdout")
        alpha = Decimal(self.alpha)
        if not Decimal("0") < alpha < Decimal("1"):
            raise ValueError("alpha is a miscoverage budget and lives strictly inside (0, 1)")
        expected_rank = conformal_rank(alpha, self.wrong_decisions_in_conformal_split)
        if self.quantile_rank != expected_rank:
            raise ValueError(
                f"the recorded rank {self.quantile_rank} is not ceil((1-alpha)*(m+1)) = "
                f"{expected_rank}; a rank that drifted is a different quantile"
            )
        should_exist = 0 < self.quantile_rank <= self.wrong_decisions_in_conformal_split
        if self.quantile_exists != should_exist:
            raise ValueError(
                "quantile_exists must follow from the rank and the wrong-margin count; a flag "
                "that disagrees with them is a claim the derivation did not produce"
            )
        if self.quantile_exists:
            if self.threshold is None:
                raise ValueError("an existing quantile names its threshold")
            if self.coverage is None:
                raise ValueError("an existing quantile reports its coverage, even a zero one")
            measured = (self.observed_error_rate, self.error_upper_bound_95)
            if self.admitted_decisions:
                if any(item is None for item in measured):
                    raise ValueError(
                        "admitted decisions carry an observed error rate and its upper bound"
                    )
            elif any(item is not None for item in measured):
                raise ValueError("a bar admitting nothing has no error rate to report")
        elif (
            self.threshold is not None
            or self.admitted_decisions
            or self.errors_admitted
            or any(
                item is not None
                for item in (
                    self.coverage,
                    self.observed_error_rate,
                    self.error_upper_bound_95,
                )
            )
        ):
            raise ValueError("a quantile that does not exist admits nothing and states nothing")
        if self.errors_admitted > self.admitted_decisions:
            raise ValueError("more errors among admitted decisions than admitted decisions")
        if self.admitted_decisions > self.certification_census.independent_decisions:
            raise ValueError("more admitted decisions than independent certification decisions")
        return self


def derive_conformal_point(
    conformal: Sequence[ScoredDecision],
    certification: Sequence[ScoredDecision],
    *,
    alpha: Decimal,
    split: str,
    calibration_source_hash: str,
    preregistration_hash: str,
    derived_at: datetime,
    previous: ConformalOperatingPointV5 | None = None,
) -> ConformalOperatingPointV5:
    """Derive the bar once, from calibration, over two disjoint independent halves.

    `previous` is how the single-shot rule survives a process restart: a caller that already
    holds a derivation passes it back, and a second derivation that does not reproduce it — a
    different alpha included — is refused. Reproducing it is the determinism proof.
    """
    if split != CALIBRATION_SPLIT:
        raise ConformalPointError(
            f"the conformal bar is derived from the {CALIBRATION_SPLIT} split only; "
            f"{split!r} is final, promotion or metamorphic evidence"
        )
    if not Decimal("0") < alpha < Decimal("1"):
        raise ConformalPointError("alpha is a miscoverage budget and lives strictly inside (0, 1)")

    censuses = {}
    for name, half in (("conformal", conformal), ("certification", certification)):
        census = DecisionCensusV4.from_feature_hashes([item.feature_hash for item in half])
        if census.replicated_decisions:
            raise ConformalPointError(
                f"{census.replicated_decisions} of {census.nominal_decisions} {name} decisions "
                "repeat another's fitted vector; a bar over replicas is a bar over one decision "
                "counted many times"
            )
        censuses[name] = census
    if not censuses["certification"].independent_decisions:
        raise ConformalPointError(
            "a bar certified against zero independent decisions certifies nothing; the "
            "certification half must not be empty"
        )
    shared = {item.feature_hash for item in conformal} & {
        item.feature_hash for item in certification
    }
    if shared:
        raise ConformalPointError(
            f"{len(shared)} fitted vectors appear in both halves; a decision that helped place "
            "the threshold cannot also be certified against it"
        )

    wrong_margins = sorted(item.score for item in conformal if item.answered and not item.correct)
    rank = conformal_rank(alpha, len(wrong_margins))
    exists = 0 < rank <= len(wrong_margins)
    threshold = wrong_margins[rank - 1] if exists else None

    admitted = (
        [
            item
            for item in certification
            if item.answered and threshold is not None and item.score > threshold
        ]
        if exists
        else []
    )
    errors = sum(1 for item in admitted if not item.correct)
    independent = censuses["certification"].independent_decisions
    coverage = Decimal(len(admitted)) / Decimal(independent) if exists and independent else None
    observed_rate = Decimal(errors) / Decimal(len(admitted)) if admitted else None
    bound = round(admitted_error_upper_bound(errors, len(admitted)), 6) if admitted else None

    body = {
        "split": split,
        "calibration_source_hash": calibration_source_hash,
        "preregistration_hash": preregistration_hash,
        "alpha": str(alpha),
        "rule": DERIVATION_RULE,
        "conformal_independent_decisions": censuses["conformal"].independent_decisions,
        "certification_independent_decisions": independent,
        "wrong_decisions_in_conformal_split": len(wrong_margins),
        "quantile_rank": rank,
        "threshold": str(threshold) if threshold is not None else None,
        "admitted_decisions": len(admitted),
        "errors_admitted": errors,
        "coverage": str(coverage) if coverage is not None else None,
        "observed_error_rate": str(observed_rate) if observed_rate is not None else None,
        "error_upper_bound_95": str(bound) if bound is not None else None,
    }
    derivation_hash = sha256(
        "\n".join(f"{key}={body[key]}" for key in sorted(body)).encode()
    ).hexdigest()

    point = ConformalOperatingPointV5(
        split=split,
        calibration_source_hash=calibration_source_hash,
        preregistration_hash=preregistration_hash,
        alpha=str(alpha),
        conformal_census=censuses["conformal"],
        certification_census=censuses["certification"],
        wrong_decisions_in_conformal_split=len(wrong_margins),
        quantile_rank=rank,
        quantile_exists=exists,
        threshold=str(threshold) if threshold is not None else None,
        admitted_decisions=len(admitted),
        errors_admitted=errors,
        coverage=str(coverage) if coverage is not None else None,
        observed_error_rate=str(observed_rate) if observed_rate is not None else None,
        error_upper_bound_95=str(bound) if bound is not None else None,
        derivation_hash=derivation_hash,
        derived_at=derived_at,
    )
    if previous is not None and previous.derivation_hash != point.derivation_hash:
        raise ConformalPointError(
            "a second, different conformal bar was derived from the same calibration split; "
            f"the sealed derivation is {previous.derivation_hash}, this one is "
            f"{point.derivation_hash}"
        )
    return point
