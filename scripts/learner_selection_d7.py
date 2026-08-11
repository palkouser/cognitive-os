#!/usr/bin/env python3
"""S21D7-034: the bar, the certification cell, the whole sweep, and §2.3's ending.

The one measurement D7 exists to make. It happens in one process because the pre-registration
forbids doing it twice: the demoted half is re-scored under the wave's direction, the
split-conformal bar is derived **once** at the frozen alpha, the fresh certification half is
scored against it, the whole risk-coverage curve is reported, and the amended §2.3 is evaluated
on the result. Nothing here is chosen — every threshold was frozen in revision 7 and every
reading was fixed by W2's step 0, before the first decision was scored.

What the three step-0 rulings change, concretely:

*S21D7-025* — a decision's identity is its four **relational** vectors in slot order, which is
the level the class reads and the level the disjointness sentence was bound to. The derivation
refuses two halves sharing one, and the census refuses a half containing a replica.

*S21D7-026* — the baseline the first-choice condition must clear is the strongest released
rung's rate over the whole certification corpus, not its rate recomputed on the admitted subset.

*S21D7-027* — the containment ordering is unseated, so "the strongest rung" is whichever of the
five released rungs the fresh corpus makes strongest. The ladder record measured that; this
script reads it rather than re-deriving it.

The bar is derived once and reproduces across a process restart by its `derivation_hash`, which
excludes the wall clock by construction. `--check` re-derives everything in a fresh process and
compares the record it would write against the record on disk, ignoring only the two timestamps.

    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d7.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d7.py --check

Read-only against three stores. No database is opened, no final, batch-B or canary body is
touched, and no promotion, lifecycle or gate record is written here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning.conformal_operating_point import (  # noqa: E402
    admitted_error_upper_bound,
    conformal_rank,
    derive_conformal_point,
)
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    ContainmentContrastiveRanker,
    RelationalGroup,
    fit_containment_direction,
    relational_numbers,
)
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    build_d5_fitting_catalogue,
)
from cognitive_os.learning.correction_catalogue_d6 import seal_d6_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import (  # noqa: E402
    build_d7_certification_catalogue,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
)
from cognitive_os.learning.relational_scans import decision_signature  # noqa: E402
from cognitive_os.learning.repair_containment import containment_ordering  # noqa: E402
from cognitive_os.learning.selective_operating_point import ScoredDecision  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-learner-selection.json"

D5_FEATURE_SEALS = EVIDENCE / "sprint-21d5-feature-seals.json"
D5_FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
D6_FEATURE_SEALS = EVIDENCE / "sprint-21d6-feature-seals.json"
D6_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d7-certification-campaign.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
D7_PRE_REGISTRATION_R8 = EVIDENCE / "sprint-21d7-pre-registration-r8.json"
D7_DIRECTION = EVIDENCE / "sprint-21d7-w2-direction.json"
D7_LADDER = EVIDENCE / "sprint-21d7-w2-ladder.json"
D7_SCAN = EVIDENCE / "sprint-21d7-w2-relational-scan.json"
D7_INVARIANCE = EVIDENCE / "sprint-21d7-invariance-regression.json"
D7_BASELINE_READING = EVIDENCE / "sprint-21d7-baseline-reading.json"
D7_SUPERSESSION = EVIDENCE / "sprint-21d7-ladder-supersession.json"
D7_DISJOINTNESS = EVIDENCE / "sprint-21d7-disjointness-clarification.json"

D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")
D6_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d6-measured")
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

REGULARIZATION = Decimal("1")
MARGIN_FLOOR = Decimal("0")
ALPHA = Decimal("0.20")
CEILING_C = Decimal("0.15")
MINIMUM_CLEAN_COVERAGE = Decimal("0.40")
MINIMUM_INDEPENDENT_DECISIONS = 100
MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS = 20
FINAL_GROUPS = 60
INFERENCE_BUDGET_MS = Decimal("250")

#: §3.4's endings by name, so a reader is never asked to infer which one fired.
ENDING_SELECT = "1_select"
ENDING_LEAK_BUDGET = "2_leak_budget_exceeded"
ENDING_MARGIN_COVERAGE = "3_margin_coverage_bound"
ENDING_BASELINE = "4_baseline_not_beaten"
ENDING_INVARIANCE = "5_invariance_violated"

#: Fields that measure this process rather than the evidence, and so cannot reproduce across a
#: restart. `--check` ignores exactly these three and nothing else: the two wall clocks, and the
#: slowest observed ranking, which is a stopwatch reading of the machine that ran it. The
#: *verdict* it feeds — `within_inference_budget` — is compared like every other number, so a
#: run that breached the 250 ms budget would still fail the comparison.
CLOCK_FIELDS = ("recorded_at", "derived_at", "maximum_inference_ms")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed_records(store: Path, seals_path: Path, partition: str) -> SealedFeatureRecordSetV2:
    row = next(item for item in _read(seals_path)["partitions"] if item["partition"] == partition)
    for path in sorted(store.rglob("*")):
        if not path.is_file() or len(path.name) != 64:
            continue
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            isinstance(candidate, dict)
            and candidate.get("content_hash") == row["feature_seal_hash"]
        ):
            if _sha256(path.read_bytes()) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


def _catalogue_maps(catalogue: Any) -> tuple[dict, dict, dict, dict]:
    """Order, candidate source, family and baseline source per group."""
    order: dict[str, tuple[str, ...]] = {}
    delta: dict[str, str] = {}
    family: dict[str, str] = {}
    baseline: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        family[group.repository_group] = group.family
        path = next(name for name in item.visible_files if name.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[path]
        for slot in group.slots:
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[
                RealityCandidateStrategy(slot.recipe)
            ][path]
    return order, delta, family, baseline


def _matrix(
    seal: SealedFeatureRecordSetV2, campaign_path: Path, *, published_hash: str
) -> FittedMatrix:
    rows = tuple(
        FittedRow(
            candidate_id=UUID(str(item["candidate_id"])),
            task_id=UUID(str(item["task_id"])),
            group=str(item["group"]),
            partition="calibration",
            vector=CorrectionFeatureVector(
                encoder_version=seal.record_for(UUID(str(item["candidate_id"]))).encoder_version,
                values=seal.record_for(UUID(str(item["candidate_id"]))).values,
                embedding=seal.record_for(UUID(str(item["candidate_id"]))).embedding,
            ),
            accepted=bool(item["accepted"]),
            sealed_at=seal.sealed_at,
            outcome_at=seal.sealed_at,
            observation_id=UUID(str(item["observation_id"])),
            sealed_feature_hash=seal.record_for(
                UUID(str(item["candidate_id"]))
            ).feature_vector_hash,
        )
        for item in _read(campaign_path)["candidate_outcomes"]
    )
    matrix = FittedMatrix(split="calibration", rows=rows)
    if matrix.content_hash != published_hash:
        raise SystemExit(
            f"the rebuilt matrix is not the published one: {matrix.content_hash} against "
            f"{published_hash}; a bar over drifted rows is a bar about nothing"
        )
    return matrix


def _groups(matrix: FittedMatrix, catalogue: Any) -> list[RelationalGroup]:
    order, delta, _, baseline = _catalogue_maps(catalogue)
    values: dict[str, dict[str, Any]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        values.setdefault(row.group, {})[str(row.candidate_id)] = row.vector.values
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
    return [
        RelationalGroup(
            group=name,
            order=order[name],
            numbers=relational_numbers(
                values[name],
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
            accepted=accepted[name],
        )
        for name in sorted(order)
    ]


def _score(
    ranker: ContainmentContrastiveRanker,
    groups: list[RelationalGroup],
    comparator_first: dict[str, str] | None,
) -> tuple[list[dict[str, Any]], Decimal]:
    """One direction over one half. Abstention only; admission is the bar's job."""
    decisions: list[dict[str, Any]] = []
    slowest = Decimal("0")
    for group in groups:
        started = datetime.now(UTC)
        ranking = ranker.rank(group.numbers, baseline_order=group.order)
        elapsed = Decimal(str(round((datetime.now(UTC) - started).total_seconds() * 1000, 3)))
        slowest = max(slowest, elapsed)
        first = None if ranking.abstained else ranking.ordered_candidate_ids[0]
        decisions.append(
            {
                "group": group.group,
                # A decision's identity is its four relational vectors in slot order — the level
                # the class reads, and the level S21D7-025 bound the disjointness sentence to.
                "signature": _digest(str(decision_signature(group.order, group.numbers))),
                "answered": not ranking.abstained,
                "score": str(ranking.confidence),
                "first_choice": first,
                "correct": bool(first is not None and group.accepted[first]),
                "changed": (
                    first is not None
                    and comparator_first is not None
                    and first != comparator_first[group.group]
                ),
                "comparator_correct": (
                    None
                    if comparator_first is None
                    else group.accepted[comparator_first[group.group]]
                ),
            }
        )
    return decisions, slowest


def _scored(decisions: list[dict[str, Any]]) -> list[ScoredDecision]:
    return [
        ScoredDecision(
            decision_id=str(item["group"]),
            feature_hash=str(item["signature"]),
            score=Decimal(str(item["score"])),
            answered=bool(item["answered"]),
            correct=bool(item["correct"]),
        )
        for item in decisions
    ]


def _sweep(decisions: list[dict[str, Any]], *, independent: int) -> list[dict[str, Any]]:
    """The whole risk-coverage curve: every distinct margin, none of them selectable.

    Not a grid. No point here may be chosen — choosing a threshold on the certification set is
    the search the pre-registration forbids. Only the derived conformal bar is a cell.
    """
    answered = [item for item in decisions if item["answered"]]
    points = []
    for threshold in sorted({Decimal(str(item["score"])) for item in answered}, reverse=True):
        admitted = [item for item in answered if Decimal(str(item["score"])) >= threshold]
        errors = [item for item in admitted if not item["correct"]]
        changed = [item for item in admitted if item["changed"]]
        points.append(
            {
                "threshold": str(threshold),
                "admitted_decisions": len(admitted),
                "errors_admitted": len(errors),
                "changed_decisions": len(changed),
                "coverage": str(Decimal(len(admitted)) / Decimal(independent)),
                "first_choice_rate_over_admitted": str(
                    Decimal(len(admitted) - len(errors)) / Decimal(len(admitted))
                ),
                "error_upper_bound_95": str(
                    round(admitted_error_upper_bound(len(errors), len(admitted)), 6)
                ),
                "selectable": False,
            }
        )
    return points


def _feasibility(sweep: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether the amended pair is reachable anywhere on this curve, not only at the bar."""
    at_floor = [point for point in sweep if Decimal(point["coverage"]) >= MINIMUM_CLEAN_COVERAGE]
    best = min((Decimal(point["error_upper_bound_95"]) for point in at_floor), default=None)
    reachable = [point for point in at_floor if Decimal(point["error_upper_bound_95"]) <= CEILING_C]
    return {
        "sweep_points": len(sweep),
        "points_at_or_above_the_coverage_floor": len(at_floor),
        "best_bound_at_or_above_the_coverage_floor": None if best is None else str(best),
        "pair_is_reachable_at_any_threshold": bool(reachable),
        "reachable_points": len(reachable),
        "what_this_separates": (
            "'unmet at this bar' from 'infeasible on this corpus'. A tighter alpha moves the bar "
            "along this same curve, so a pair no point satisfies is not a volume question"
        ),
    }


def _cell(
    *,
    decisions: list[dict[str, Any]],
    point: Any,
    independent: int,
    baseline_rate: Decimal,
    baseline_name: str,
    slowest: Decimal,
) -> dict[str, Any]:
    answered = [item for item in decisions if item["answered"]]
    threshold = None if point.threshold is None else Decimal(point.threshold)
    admitted = [
        item
        for item in answered
        if threshold is not None and Decimal(str(item["score"])) > threshold
    ]
    errors = [item for item in admitted if not item["correct"]]
    changed = [item for item in admitted if item["changed"]]
    wrong_answered = [item for item in answered if not item["correct"]]
    leak_rate = Decimal(len(errors)) / Decimal(len(wrong_answered)) if wrong_answered else None
    coverage = Decimal(len(admitted)) / Decimal(independent)
    first_choice = (
        Decimal(len(admitted) - len(errors)) / Decimal(len(admitted)) if admitted else None
    )
    projected = (
        Decimal(len(changed)) / Decimal(len(admitted)) * FINAL_GROUPS if admitted else Decimal(0)
    )
    bound = (
        Decimal(str(round(admitted_error_upper_bound(len(errors), len(admitted)), 6)))
        if admitted
        else None
    )
    return {
        "operating_point": "split_conformal",
        "hypothesis_class": HYPOTHESIS_CLASS,
        "cells": 1,
        "alpha": str(ALPHA),
        "threshold": None if threshold is None else str(threshold),
        "independent_decisions": independent,
        "nominal_decisions": len(decisions),
        "answered_decisions": len(answered),
        "admitted_decisions": len(admitted),
        "coverage": str(coverage),
        "coverage_denominator": "independent_decisions",
        "first_choice_rate_over_admitted": None if first_choice is None else str(first_choice),
        "baseline_first_choice_rate": str(baseline_rate),
        "baseline_rung": baseline_name,
        "baseline_reading": "whole_corpus, per S21D7-026",
        "beats_the_baseline": bool(first_choice is not None and first_choice > baseline_rate),
        "errors_admitted": len(errors),
        "observed_error_rate_over_admitted": None
        if not admitted
        else str(Decimal(len(errors)) / Decimal(len(admitted))),
        "error_upper_bound_95": None if bound is None else str(bound),
        "ceiling_c": str(CEILING_C),
        "within_the_ceiling": bool(bound is not None and bound <= CEILING_C),
        "leak": {
            "wrong_answered_decisions": len(wrong_answered),
            "wrong_answered_decisions_admitted": len(errors),
            "realised_leak_rate": None if leak_rate is None else str(leak_rate),
            "alpha_leak_budget": str(ALPHA),
            "within_the_leak_budget": bool(leak_rate is not None and leak_rate <= ALPHA),
            "what_it_is": (
                "P(admitted | the decision is wrong), measured on the certification half. This "
                "is the quantity alpha bounds; the error rate among admitted decisions is a "
                "different number and is what the amended §2.3 reads"
            ),
        },
        "changed_decisions": len(changed),
        "projected_changed_final_decisions": str(round(projected, 3)),
        "maximum_inference_ms": str(slowest),
        "within_inference_budget": slowest <= INFERENCE_BUDGET_MS,
        "fully_abstaining": not answered,
        "filtered_no_changed_decision": not changed,
    }


def _conditions(
    cell: dict[str, Any], *, first_action_preserved: bool, sweep_points: int
) -> list[str]:
    """Every amended §2.3 condition this cell fails, by name. An empty list is eligibility."""
    reasons: list[str] = []
    if int(cell["independent_decisions"]) < MINIMUM_INDEPENDENT_DECISIONS:
        reasons.append("fewer_than_100_independent_clean_decisions")
    if not cell["admitted_decisions"]:
        reasons.append("the_bar_admitted_nothing")
    elif not cell["within_the_ceiling"]:
        reasons.append("clopper_pearson_95_upper_bound_above_0.15")
    if Decimal(str(cell["coverage"])) < MINIMUM_CLEAN_COVERAGE:
        reasons.append("clean_coverage_below_0.40")
    if Decimal(str(cell["projected_changed_final_decisions"])) < (
        MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS
    ):
        reasons.append("fewer_than_20_projected_changed_final_decisions")
    if not cell["beats_the_baseline"]:
        reasons.append("first_choice_rate_not_above_the_strongest_baseline")
    if int(cell["changed_decisions"]) < 1:
        reasons.append("no_changed_clean_decision")
    if not cell["within_inference_budget"]:
        reasons.append("inference_budget_exceeded")
    if not first_action_preserved:
        reasons.append("first_action_not_preserved_on_the_invariance_sample")
    if not sweep_points:
        reasons.append("no_sweep_point_reported")
    return reasons


def _ending(
    cell: dict[str, Any],
    reasons: list[str],
    *,
    first_action_preserved: bool,
    feasibility: dict[str, Any],
) -> tuple[str, str]:
    """§3.4's tree, evaluated once on the one cell. The record must not guess."""
    if not reasons:
        return ENDING_SELECT, (
            "every amended §2.3 condition holds on the one pre-registered cell: at least 100 "
            "independent clean decisions, admission by the split-conformal bar at alpha with a "
            "Clopper-Pearson 95% upper bound at or below 0.15, coverage at least 0.40, at least "
            "20 projected changed final decisions, a first-choice rate strictly above the "
            "strongest released rung's whole-corpus rate, at least one changed decision, "
            "100% first-action preservation, every sweep point reported and inference inside "
            "the 250 ms budget. Selection proceeds"
        )
    if not first_action_preserved:
        return ENDING_INVARIANCE, (
            "step 5: a first action moved on the invariance sample. The containment share cannot "
            "move under the six frozen cases by construction, so this indicts the scalar half or "
            "the assembly rather than the signal"
        )
    coverage = Decimal(str(cell["coverage"]))
    if coverage < MINIMUM_CLEAN_COVERAGE:
        return ENDING_MARGIN_COVERAGE, (
            f"step 3: clean coverage is {coverage} at the pre-registered alpha {ALPHA}, below the "
            f"{MINIMUM_CLEAN_COVERAGE} floor. The class ranks, but its margin does not "
            "concentrate errors at low margins on evidence nobody had read. The containment "
            "rung's own measured rate on this corpus says whether the signal or the fit failed"
        )
    if not cell["within_the_ceiling"]:
        leak = cell["leak"]
        held = (
            f"the bar held its leak guarantee — {leak['wrong_answered_decisions_admitted']} of "
            f"{leak['wrong_answered_decisions']} wrong decisions cleared it, a realised leak of "
            f"{leak['realised_leak_rate']} against the {ALPHA} budget — and the admitted "
            "precision still missed"
        )
        missed = (
            f"the realised leak is {leak['realised_leak_rate']}, itself above the {ALPHA} budget. "
            "Step 2 is worded for a bar that held its guarantee and missed the ceiling anyway; "
            "this one missed both, which is the exchangeability symptom rather than a defect in "
            "the rule, and it is recorded here rather than smoothed into the typed ending"
        )
        tail = (
            " A tighter alpha moves the bar along the same curve, and no point of this "
            f"{feasibility['sweep_points']}-point sweep satisfies the amended pair at all — the "
            "best bound at or above the coverage floor is "
            f"{feasibility['best_bound_at_or_above_the_coverage_floor']} — so what binds is the "
            "class's error rate on this corpus, not conformal-half volume"
            if not feasibility["pair_is_reachable_at_any_threshold"]
            else (
                f" {feasibility['reachable_points']} points of this "
                f"{feasibility['sweep_points']}-point sweep do satisfy the amended pair, so the "
                "pair is reachable on this corpus and the bar is what missed it"
            )
        )
        return ENDING_LEAK_BUDGET, (
            f"step 2: coverage is {coverage}, at or above the floor, and the Clopper-Pearson 95% "
            f"upper bound on the error rate among admitted decisions is "
            f"{cell['error_upper_bound_95']}, above the pre-registered ceiling {CEILING_C}. "
            + (held if leak["within_the_leak_budget"] else missed)
            + "."
            + tail
        )
    if not cell["beats_the_baseline"]:
        return ENDING_BASELINE, (
            f"step 4: the first-choice rate over admitted decisions is "
            f"{cell['first_choice_rate_over_admitted']}, not strictly above the strongest "
            f"released rung {cell['baseline_rung']} at {cell['baseline_first_choice_rate']} over "
            "the whole corpus. Under S21D7-027 the containment rung is unseated, so this is the "
            "released ladder's own baseline and the finding is that the fitted class does not "
            "beat it"
        )
    return ENDING_LEAK_BUDGET, (
        "coverage, the bound and the baseline all hold and a different §2.3 condition failed; "
        f"the failing conditions are named in `failed_conditions`: {reasons}. §3.4 types no "
        "ending for this shape, so the nearest one is recorded together with the reason it is "
        "not a clean fit, rather than inventing a sixth ending after the measurement"
    )


def _direction() -> Any:
    seal = _sealed_records(D5_ARTIFACT_ROOT, D5_FEATURE_SEALS, "training")
    catalogue = build_d5_fitting_catalogue()
    order, delta, _, baseline = _catalogue_maps(catalogue)
    values = {str(record.candidate_id): record.values for record in seal.records}
    labels: dict[str, dict[str, bool]] = {}
    for item in _read(D5_FITTING_CAMPAIGN)["candidate_outcomes"]:
        labels.setdefault(str(item["group"]), {})[str(item["candidate_id"])] = bool(
            item["accepted"]
        )
    groups = [
        RelationalGroup(
            group=name,
            order=order[name],
            numbers=relational_numbers(
                {item: values[item] for item in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
            accepted=labels[name],
        )
        for name in sorted(order)
    ]
    model = fit_containment_direction(groups, regularization=REGULARIZATION)
    sealed_hash = _read(D7_DIRECTION)["fit"]["model_hash"]
    if model.content_hash() != sealed_hash:
        raise SystemExit(
            f"the direction does not match the one W2 sealed: {model.content_hash()} against "
            f"{sealed_hash}. The wave fits once; this script re-derives it only to prove it"
        )
    return model


def _build(write: bool) -> dict[str, Any]:
    snapshots = _read(D7_SNAPSHOTS)["fitted_matrices"]
    ladder = _read(D7_LADDER)
    invariance = _read(D7_INVARIANCE)

    model = _direction()
    ranker = ContainmentContrastiveRanker(model, margin_floor=MARGIN_FLOOR)

    # --- the demoted half places the bar and certifies nothing ------------------------------
    bar_seal = _sealed_records(D6_ARTIFACT_ROOT, D6_FEATURE_SEALS, "calibration")
    bar_matrix = _matrix(
        bar_seal,
        D6_CERTIFICATION_CAMPAIGN,
        published_hash=snapshots["conformal_matrix_hash"],
    )
    bar_catalogue = seal_d6_corpus().catalogues[CorrectionPartition.CALIBRATION]
    bar_decisions, _ = _score(ranker, _groups(bar_matrix, bar_catalogue), None)

    # --- the fresh half is certified against it ---------------------------------------------
    cert_seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")
    cert_matrix = _matrix(
        cert_seal,
        D7_CERTIFICATION_CAMPAIGN,
        published_hash=snapshots["certification_matrix_hash"],
    )
    cert_catalogue = build_d7_certification_catalogue()
    cert_groups = _groups(cert_matrix, cert_catalogue)

    # The comparator §2.3 pairs changed decisions against, read from the sealed ladder record
    # rather than re-derived: S21D7-027 unseated the containment rung, so this is whichever of
    # the five released rungs the fresh corpus made strongest.
    baseline_name = ladder["released_rungs"]["strongest_non_learned_name"]
    baseline_rate = Decimal(ladder["released_rungs"]["strongest_non_learned_rate"])
    order, delta, family, baseline_source = _catalogue_maps(cert_catalogue)
    rung_ordering = eligible_rungs(cert_matrix.rows[0].vector.encoder_version)[baseline_name]
    requirement = {}
    for group in cert_catalogue.groups:
        item = template(group.template_id)
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
    comparator_first = {
        item.group: rung_ordering(item)[0]
        for item in group_candidates(
            cert_matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }
    cert_decisions, slowest = _score(ranker, cert_groups, comparator_first)

    # The two numbers a pass under S21D7-026 and S21D7-027 must be read against, computed here
    # so the record cannot be read as claiming more than it measured. Neither binds: the rung's
    # rate on the admitted subset is the reading the ruling did *not* take, and the containment
    # ordering is unseated. Both are reported because a pass whose margin comes from a ruling
    # should show what the other side of that ruling would have said.
    containment_first = {
        name: containment_ordering(
            baseline_source[name],
            {item: delta[item] for item in order[name]},
            baseline_order=order[name],
        )[0]
        for name in order
    }
    accepted_by_group = {group.group: group.accepted for group in cert_groups}

    # --- the bar, derived once ---------------------------------------------------------------
    point = derive_conformal_point(
        _scored(bar_decisions),
        _scored(cert_decisions),
        alpha=ALPHA,
        split="calibration",
        calibration_source_hash=bar_matrix.content_hash,
        preregistration_hash=_sha256(D7_PRE_REGISTRATION_R8.read_bytes()),
        derived_at=utc_now(),
    )
    independent = point.certification_census.independent_decisions
    cell = _cell(
        decisions=cert_decisions,
        point=point,
        independent=independent,
        baseline_rate=baseline_rate,
        baseline_name=baseline_name,
        slowest=slowest,
    )
    sweep = _sweep(cert_decisions, independent=independent)
    feasibility = _feasibility(sweep)
    first_action_preserved = invariance["first_action"]["changes"] == 0
    reasons = _conditions(
        cell, first_action_preserved=first_action_preserved, sweep_points=len(sweep)
    )
    ending, reading = _ending(
        cell, reasons, first_action_preserved=first_action_preserved, feasibility=feasibility
    )

    admitted_groups = [
        item["group"]
        for item in cert_decisions
        if item["answered"]
        and point.threshold is not None
        and Decimal(str(item["score"])) > Decimal(point.threshold)
    ]
    admitted_first = {
        item["group"]: item["first_choice"]
        for item in cert_decisions
        if item["group"] in set(admitted_groups)
    }
    rung_on_admitted = sum(
        1 for name in admitted_groups if accepted_by_group[name][comparator_first[name]]
    )
    containment_on_admitted = sum(
        1 for name in admitted_groups if accepted_by_group[name][containment_first[name]]
    )
    changed_vs_containment = sum(
        1 for name in admitted_groups if admitted_first[name] != containment_first[name]
    )
    containment_rate = Decimal(ladder["containment_ordering_unseated"]["first_choice_rate"])
    readings = {
        "binding_reading": "whole_corpus, per S21D7-026",
        "admitted_subset_reading_not_taken": {
            "comparator": baseline_name,
            "rate_on_the_admitted_decisions": None
            if not admitted_groups
            else str(Decimal(rung_on_admitted) / Decimal(len(admitted_groups))),
            "class_would_still_beat_it": bool(
                admitted_groups
                and Decimal(len(admitted_groups) - cell["errors_admitted"])
                / Decimal(len(admitted_groups))
                > Decimal(rung_on_admitted) / Decimal(len(admitted_groups))
            ),
            "why_it_is_here": (
                "S21D7-026 took the whole-corpus reading and recorded that it is the weaker of "
                "the two. This is the number it did not take, reported so the pass is read as "
                "what it is rather than as the stronger claim"
            ),
        },
        "seated_pairing_not_in_force": {
            "comparator": "repair_containment_ordering, unseated by S21D7-027",
            "whole_corpus_rate": str(containment_rate),
            "rate_on_the_admitted_decisions": None
            if not admitted_groups
            else str(Decimal(containment_on_admitted) / Decimal(len(admitted_groups))),
            "changed_decisions_against_it": changed_vs_containment,
            "projected_changed_final_decisions": None
            if not admitted_groups
            else str(
                round(
                    Decimal(changed_vs_containment) / Decimal(len(admitted_groups)) * FINAL_GROUPS,
                    3,
                )
            ),
            "would_have_met_the_changed_decision_floor": bool(
                admitted_groups
                and Decimal(changed_vs_containment) / Decimal(len(admitted_groups)) * FINAL_GROUPS
                >= MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS
            ),
            "would_have_met_the_baseline_condition": bool(
                admitted_groups
                and Decimal(len(admitted_groups) - cell["errors_admitted"])
                / Decimal(len(admitted_groups))
                > containment_rate
            ),
            "why_it_is_here": (
                "the ruling that unseated this rung is the one that moved the baseline, and a "
                "record whose pass depends on a ruling has to publish what the other branch "
                "would have said. These two flags are that, and neither is a condition"
            ),
        },
    }

    by_family: dict[str, dict[str, int]] = {}
    for decision in cert_decisions:
        name = family[decision["group"]]
        bucket = by_family.setdefault(
            name, {"decisions": 0, "correct": 0, "admitted": 0, "changed": 0}
        )
        bucket["decisions"] += 1
        bucket["correct"] += int(decision["correct"])
        if point.threshold is not None and Decimal(str(decision["score"])) > Decimal(
            point.threshold
        ):
            bucket["admitted"] += 1
            bucket["changed"] += int(decision["changed"])

    record = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W2",
        "stage": "selection",
        "items": ["S21D7-034"],
        "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "stores_opened_for_writing": 0,
        "bars_derived": 1,
        "directions_fitted": 0,
        "inputs": {
            "d5_feature_seals_sha256": _sha256(D5_FEATURE_SEALS.read_bytes()),
            "d6_feature_seals_sha256": _sha256(D6_FEATURE_SEALS.read_bytes()),
            "d7_feature_seals_sha256": _sha256(D7_FEATURE_SEALS.read_bytes()),
            "d7_certification_campaign_sha256": _sha256(D7_CERTIFICATION_CAMPAIGN.read_bytes()),
            "d6_certification_campaign_sha256": _sha256(D6_CERTIFICATION_CAMPAIGN.read_bytes()),
            "d7_contracts_sha256": _sha256(D7_CONTRACTS.read_bytes()),
            "d7_pre_registration_r8_sha256": _sha256(D7_PRE_REGISTRATION_R8.read_bytes()),
            "w2_direction_sha256": _sha256(D7_DIRECTION.read_bytes()),
            "w2_ladder_sha256": _sha256(D7_LADDER.read_bytes()),
            "w2_relational_scan_sha256": _sha256(D7_SCAN.read_bytes()),
            "invariance_regression_sha256": _sha256(D7_INVARIANCE.read_bytes()),
            "bar_setting_matrix_hash": bar_matrix.content_hash,
            "certification_matrix_hash": cert_matrix.content_hash,
            "model_hash": model.content_hash(),
        },
        "rulings_this_record_is_evaluated_under": {
            "S21D7-025": _read(D7_DISJOINTNESS)["integrity_content_hash"],
            "S21D7-026": _read(D7_BASELINE_READING)["integrity_content_hash"],
            "S21D7-027": _read(D7_SUPERSESSION)["integrity_content_hash"],
        },
        "bar_setting_half": {
            "source": "the demoted D6 certification half, per S21D7-010",
            "groups": len(bar_decisions),
            "answered_decisions": sum(1 for item in bar_decisions if item["answered"]),
            "wrong_answered_decisions": sum(
                1 for item in bar_decisions if item["answered"] and not item["correct"]
            ),
            "first_choice_rate": str(
                Decimal(sum(1 for item in bar_decisions if item["correct"]))
                / Decimal(len(bar_decisions))
            ),
            "quantile_rank_at_alpha": conformal_rank(
                ALPHA, sum(1 for item in bar_decisions if item["answered"] and not item["correct"])
            ),
            "certifies": "nothing",
        },
        "conformal_point": {
            "quantile_exists": point.quantile_exists,
            "threshold": point.threshold,
            "alpha": point.alpha,
            "wrong_decisions_in_conformal_split": point.wrong_decisions_in_conformal_split,
            "quantile_rank": point.quantile_rank,
            "admitted_decisions": point.admitted_decisions,
            "errors_admitted": point.errors_admitted,
            "coverage": point.coverage,
            "observed_error_rate": point.observed_error_rate,
            "error_upper_bound_95": point.error_upper_bound_95,
            "derivation_hash": point.derivation_hash,
            "derived_at": point.derived_at.isoformat(),
            "split": point.split,
            "calibration_source_hash": point.calibration_source_hash,
            "preregistration_hash": point.preregistration_hash,
            "conformal_census": point.conformal_census.model_dump(
                mode="json", exclude={"content_hash"}
            ),
            "certification_census": point.certification_census.model_dump(
                mode="json", exclude={"content_hash"}
            ),
            "derived_once": (
                "the derivation hash excludes the wall clock, so a second process re-deriving "
                "it either reproduces this value or the bar moved"
            ),
        },
        "cell": cell,
        "per_family": {name: by_family[name] for name in sorted(by_family)},
        "sweep": {
            "points": len(sweep),
            "every_point_reported": True,
            "selectable_points": 0,
            "curve": sweep,
            "feasibility": feasibility,
        },
        "invariance": {
            "record": D7_INVARIANCE.name,
            "integrity_content_hash": invariance["integrity_content_hash"],
            "cases": invariance["first_action"]["cases_compared"],
            "first_action_changes": invariance["first_action"]["changes"],
            "preserved": first_action_preserved,
        },
        "section_2_3": {
            "conditions": 9,
            "failed_conditions": reasons,
            "eligible": not reasons,
            "baseline_reading": "whole_corpus, per S21D7-026",
            "changed_decisions_pair_against": baseline_name,
            "readings_reported_beside_the_binding_one": readings,
        },
        "ending": {
            "name": ending,
            "reading": reading,
            "no_ending_may_be_chosen_after_the_measurement": True,
            "endings_are_six_different_sprints": True,
        },
        "what_this_record_is_not": (
            "a promotion. Selection eligibility is what §2.3 decides; binding the artifact, "
            "running the lifecycle and closing the gate are later steps with their own records"
        ),
    }
    record["integrity_content_hash"] = _sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    )
    text = json.dumps(record, indent=1, sort_keys=True) + "\n"
    if write:
        OUTPUT.write_text(text, encoding="utf-8")
    else:
        _compare(record)
    return record


def _strip(record: dict[str, Any]) -> str:
    """The record without the three fields that measure the process rather than the evidence."""
    payload = json.loads(json.dumps(record))
    payload.pop("integrity_content_hash", None)
    for field in CLOCK_FIELDS:
        payload.pop(field, None)
        payload.get("conformal_point", {}).pop(field, None)
        payload.get("cell", {}).pop(field, None)
    return json.dumps(payload, indent=1, sort_keys=True)


def _compare(record: dict[str, Any]) -> None:
    if not OUTPUT.exists():
        raise SystemExit(f"{OUTPUT.name} does not exist; there is nothing to reproduce")
    stored = _read(OUTPUT)
    if _strip(stored) != _strip(record):
        raise SystemExit(
            f"{OUTPUT.name} does not match the record this script derives. The bar, the cell or "
            "the sweep moved across a process restart, which is a determinism defect and a stop"
        )
    if stored["conformal_point"]["derivation_hash"] != record["conformal_point"]["derivation_hash"]:
        raise SystemExit("the conformal derivation hash did not reproduce")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="re-derive the bar and the cell in this process and compare; writes nothing",
    )
    write = not parser.parse_args().check
    record = _build(write)
    print(
        json.dumps(
            {
                "mode": "write" if write else "check",
                "threshold": record["conformal_point"]["threshold"],
                "derivation_hash": record["conformal_point"]["derivation_hash"],
                "admitted": record["cell"]["admitted_decisions"],
                "coverage": record["cell"]["coverage"],
                "errors_admitted": record["cell"]["errors_admitted"],
                "error_upper_bound_95": record["cell"]["error_upper_bound_95"],
                "first_choice_over_admitted": record["cell"]["first_choice_rate_over_admitted"],
                "baseline": [
                    record["cell"]["baseline_rung"],
                    record["cell"]["baseline_first_choice_rate"],
                ],
                "changed_decisions": record["cell"]["changed_decisions"],
                "projected_changed_final_decisions": record["cell"][
                    "projected_changed_final_decisions"
                ],
                "failed_conditions": record["section_2_3"]["failed_conditions"],
                "ending": record["ending"]["name"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if record["ending"]["name"] == ENDING_SELECT else 1


if __name__ == "__main__":
    raise SystemExit(main())
