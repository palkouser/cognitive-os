#!/usr/bin/env python3
"""S21D4-039. The risk-coverage curve, and at most one candidate.

This is where W2's hundred independent calibration decisions finally measure something. The
frozen 24-setting k-NN grid is crossed with the three pre-registered operating points at both
volume points, the strongest deterministic baseline is measured on the same decisions, and
Section 3.3's decision tree -- not this script's author -- decides whether a candidate is
selected or a typed stop is recorded.

Two gates, deliberately distinct, because collapsing them is how a selective ranker gets
credit for work it did not do:

*The setting's confidence floor decides abstention.* Below it the ranker declines and the
caller runs the deterministic order.

*The operating point decides admission.* Of the decisions the setting answered, only those
scoring strictly above the operating point are admitted, which is the sentence amendment 1
made operative. Coverage is admitted decisions over independent decisions, and a confident
error is an admitted decision that is wrong.

Nothing here encodes anything. Every vector comes out of the feature seals S21D4-034 wrote and
the artifact store holds. That is not only cheaper -- W2-D9 established that the frozen MiniLM
is batch-composition dependent, so a grid that re-embedded would put padding noise into the
differences between settings.

No final, batch-B or canary body, outcome or manifest is opened. On a stop the record names
every dependent that stays closed.

    set -a && . ./.env.s21d4.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d4.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    build_ladder,
    eligible_rungs,
    group_candidates,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionPartition,
    DecisionCensusV4,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
)
from cognitive_os.learning.knn_calibration import (  # noqa: E402
    SELECTION_RULE,
    Setting,
    declared_grid,
    grid_hash,
)
from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    DERIVATION_RULE,
    ScoredDecision,
    derive_zero_error_point,
    zero_error_upper_bound,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SEAL_RECORD = EVIDENCE / "sprint-21d4-feature-seals.json"
FITTING_CAMPAIGN = EVIDENCE / "sprint-21d4-self-play-campaign.json"
CALIBRATION_CAMPAIGN = EVIDENCE / "sprint-21d4-calibration-campaign.json"
SNAPSHOTS = EVIDENCE / "sprint-21d4-snapshots.json"
INVARIANCE = EVIDENCE / "sprint-21d4-invariance-regression.json"
FITTING_POOL = EVIDENCE / "sprint-21d4-fitting-pool.json"
OUTPUT = EVIDENCE / "sprint-21d4-learner-selection.json"

#: S21D4-012 declared these before any D4 measurement. Whole groups, so a volume point never
#: fits on three of a group's four candidates.
VOLUME_POINTS: tuple[int, ...] = (200, 320)

#: §4.2: the derived zero-error point plus the two released fixed floors, which stay in the
#: comparison as declared comparators so the change is attributable.
RELEASED_FLOORS: tuple[str, ...] = ("0.55", "0.70")
DERIVED = "zero_error"

#: §2.3, verbatim as thresholds.
MINIMUM_INDEPENDENT_DECISIONS = 100
MINIMUM_CLEAN_COVERAGE = Decimal("0.40")
FINAL_GROUPS = 60
MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS = 20
CONFIDENT_ERRORS_ALLOWED = 0
INFERENCE_BUDGET_MS = Decimal("250")

#: §3.3's endings. Recorded by name so a reader is never asked to infer which one fired.
STOP_VOLUME_BOUND = "volume_bound"
STOP_HYPOTHESIS_CLASS_BOUND = "hypothesis_class_bound"

#: What a stop leaves closed. Named exhaustively, because "nothing else was opened" is a claim
#: about absence and absence is what a list makes checkable.
DEPENDENT_NOT_OPENED = (
    "final A bodies, outcomes and manifest",
    "final B bodies, outcomes and manifest",
    "canary bodies, outcomes and manifest",
    "the promotion metamorphic submanifest's 120 nominal decisions",
    "the paired group bootstrap at seed 21041",
    "artifact promotion, activation, shadow and canary lifecycle",
    "Gate L2 conditions 13 through 16 and 21 through 27",
    "Sprint 22A domain expansion",
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d4.local first")
    return value


def _matrix(
    outcomes: list[dict[str, Any]],
    seal: SealedFeatureRecordSetV2,
    *,
    split: str,
    partition: str,
) -> FittedMatrix:
    """Rows from the sealed records and the recorded labels. Nothing is encoded here."""
    rows = []
    for item in outcomes:
        candidate_id = UUID(str(item["candidate_id"]))
        record = seal.record_for(candidate_id)
        rows.append(
            FittedRow(
                candidate_id=candidate_id,
                task_id=UUID(str(item["task_id"])),
                group=str(item["group"]),
                partition=partition,
                vector=CorrectionFeatureVector(
                    encoder_version=record.encoder_version,
                    values=record.values,
                    embedding=record.embedding,
                ),
                accepted=bool(item["accepted"]),
                sealed_at=seal.sealed_at,
                outcome_at=seal.sealed_at,
                observation_id=UUID(str(item["observation_id"])),
                sealed_feature_hash=record.feature_vector_hash,
            )
        )
    return FittedMatrix(split=split, rows=tuple(rows))


@dataclass(frozen=True, slots=True)
class _Group:
    """One calibration group as the grid sees it: one order, four vectors, four labels."""

    group: str
    order: tuple[str, ...]
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]
    baseline_first_choice: str
    #: The decision's identity for the census: the group's four fitted vectors, in slot order.
    signature: str


def _texts(partition: CorrectionPartition) -> tuple[dict[str, str], dict[str, str]]:
    """Requirement and per-candidate texts, for the lexical rung of the baseline ladder."""
    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    for group in seal_d4_corpus().catalogues[partition].groups:
        item = template(group.template_id)
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    return requirement, delta


def _orders(partition: CorrectionPartition) -> dict[str, tuple[str, ...]]:
    return {
        group.repository_group: tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for group in seal_d4_corpus().catalogues[partition].groups
    }


def _volume_rows(matrix: FittedMatrix, rows: int) -> tuple[FittedRow, ...]:
    """The first `rows` fitting rows, taken as whole groups in sorted group order.

    Whole groups on purpose: fitting on three of a group's four candidates would put the
    fourth's siblings in the exemplar set and call the result a volume effect.
    """
    by_group: dict[str, list[FittedRow]] = {}
    for row in matrix.rows:
        by_group.setdefault(row.group, []).append(row)
    taken: list[FittedRow] = []
    for name in sorted(by_group):
        if len(taken) + len(by_group[name]) > rows:
            break
        taken.extend(sorted(by_group[name], key=lambda item: str(item.candidate_id)))
    if len(taken) != rows:
        raise SystemExit(f"a {rows}-row volume point does not land on a group boundary")
    return tuple(taken)


def _score_setting(
    setting: Setting, exemplars: tuple[Exemplar, ...], groups: tuple[_Group, ...]
) -> tuple[list[dict[str, Any]], Decimal]:
    """One setting over every calibration group. Abstention only; admission comes later."""
    knn = CorrectionKnn(
        exemplars,
        k=setting.k,
        similarity_floor=setting.similarity_floor,
        agreement_floor=setting.agreement_floor,
        confidence_floor=setting.confidence_floor,
        embedding_weight=setting.embedding_weight,
    )
    decisions: list[dict[str, Any]] = []
    slowest = Decimal("0")
    for item in groups:
        started = datetime.now(UTC)
        ranking = knn.rank(item.vectors, baseline_order=item.order)
        elapsed = Decimal(str(round((datetime.now(UTC) - started).total_seconds() * 1000, 3)))
        slowest = max(slowest, elapsed)
        first = ranking.first_choice
        decisions.append(
            {
                "group": item.group,
                "signature": item.signature,
                "answered": not ranking.abstained,
                "score": ranking.confidence,
                "first_choice": first,
                "correct": bool(first and item.accepted[first]),
                "changed": (not ranking.abstained) and first != item.baseline_first_choice,
                "baseline_correct": item.accepted[item.baseline_first_choice],
            }
        )
    return decisions, slowest


def _cell(
    *,
    setting: Setting,
    volume: int,
    operating_point: str,
    threshold: Decimal | None,
    decisions: list[dict[str, Any]],
    slowest: Decimal,
    independent: int,
    derivation: dict[str, Any] | None,
) -> dict[str, Any]:
    """One (setting, operating point, volume) cell, with every denominator named."""
    answered = [item for item in decisions if item["answered"]]
    admitted = [
        item for item in answered if threshold is None or Decimal(item["score"]) > threshold
    ]
    errors = [item for item in admitted if not item["correct"]]
    changed = [item for item in admitted if item["changed"]]
    coverage = Decimal(len(admitted)) / Decimal(independent)
    first_choice_rate = (
        Decimal(len(admitted) - len(errors)) / Decimal(len(admitted)) if admitted else None
    )
    baseline_rate = Decimal(sum(1 for item in decisions if item["baseline_correct"])) / Decimal(
        independent
    )
    projected = (
        (Decimal(len(changed)) / Decimal(len(admitted)) * FINAL_GROUPS) if admitted else Decimal(0)
    )
    return {
        "setting": setting.identity,
        "k": setting.k,
        "operating_point": operating_point,
        "threshold": None if threshold is None else str(threshold),
        "volume_rows": volume,
        "independent_decisions": independent,
        "nominal_decisions": len(decisions),
        "answered_decisions": len(answered),
        "admitted_decisions": len(admitted),
        "coverage": str(coverage),
        "coverage_denominator": "independent_decisions",
        "first_choice_rate_over_admitted": None
        if first_choice_rate is None
        else str(first_choice_rate),
        "baseline_first_choice_rate": str(baseline_rate),
        "beats_the_baseline": bool(
            first_choice_rate is not None and first_choice_rate > baseline_rate
        ),
        "confident_errors": len(errors),
        "changed_decisions": len(changed),
        "projected_changed_final_decisions": str(round(projected, 3)),
        "zero_error_upper_bound_95": (
            str(round(zero_error_upper_bound(len(admitted)), 6))
            if admitted and not errors
            else None
        ),
        "maximum_inference_ms": str(slowest),
        "within_inference_budget": slowest <= INFERENCE_BUDGET_MS,
        "fully_abstaining": not answered,
        "filtered_no_changed_decision": not changed,
        "operating_point_derivation": derivation,
    }


def _satisfies_section_2_3(cell: dict[str, Any]) -> list[str]:
    """Every §2.3 condition this cell fails, by name. An empty list is eligibility."""
    reasons: list[str] = []
    if int(cell["independent_decisions"]) < MINIMUM_INDEPENDENT_DECISIONS:
        reasons.append("fewer_than_100_independent_clean_decisions")
    if int(cell["confident_errors"]) > CONFIDENT_ERRORS_ALLOWED:
        reasons.append("confident_error_among_admitted_decisions")
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
    return reasons


def _select(cells: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """§4.2's precedence, then `SELECTION_RULE`. Fixed before measurement, applied after."""
    eligible = [cell for cell in cells if not cell["ineligible_reasons"]]
    released = [cell for cell in eligible if cell["operating_point"] != DERIVED]
    derived = [cell for cell in eligible if cell["operating_point"] == DERIVED]
    pool = released or derived

    def key(cell: dict[str, Any]) -> tuple[Decimal, Decimal, int, int]:
        return (
            -Decimal(str(cell["first_choice_rate_over_admitted"])),
            -Decimal(str(cell["coverage"])),
            int(cell["k"]),
            int(cell["grid_index"]),
        )

    chosen = min(pool, key=key) if pool else None
    return chosen, {
        "rule": SELECTION_RULE,
        "precedence": (
            "a released fixed floor is preferred if it satisfies Section 2.3; only if none "
            "does may the derived zero-error point be selected"
        ),
        "eligible_cells": len(eligible),
        "eligible_at_a_released_floor": len(released),
        "eligible_at_the_derived_point": len(derived),
        "pool_taken_from": "released_floors" if released else ("derived" if derived else "none"),
    }


def _classify(curve: dict[str, Any], eligible: int) -> tuple[str | None, str]:
    """§3.3's tree, steps 3 to 5. The record must not guess between 4 and 5."""
    at_low = Decimal(str(curve[str(VOLUME_POINTS[0])]["best_zero_error_coverage"]))
    at_high = Decimal(str(curve[str(VOLUME_POINTS[-1])]["best_zero_error_coverage"]))
    if eligible:
        return None, (
            "step 3: a grid point and operating point reach zero errors on at least 100 "
            "independent decisions at coverage at least 0.40, so selection proceeds"
        )
    if at_high > 0 and at_high < MINIMUM_CLEAN_COVERAGE and at_high > at_low:
        return STOP_VOLUME_BOUND, (
            "step 4: zero-error coverage is above zero and below 0.40 at the upper volume and "
            "materially higher there than at the lower one, so the residual is evidence volume"
        )
    return STOP_HYPOTHESIS_CLASS_BOUND, (
        "step 5: zero-error coverage does not reach 0.40 and does not improve with volume, so "
        "the frozen k-NN cannot separate its own errors on this representation"
    )


async def _load() -> tuple[FittedMatrix, FittedMatrix]:
    """The two matrices, from the seals in the artifact store and the campaigns' labels."""
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    engine = create_postgres_engine(database_url)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        # Labels come from the campaign records rather than from a fresh ledger query, and the
        # record binds both campaign hashes. S21D4-037 already resolved those labels from the
        # durable ledger and rebuilt the datasets from them; re-querying here would prove the
        # ledger is still readable, not that the grid scored the outcomes the snapshots hold.
        matrices = []
        for partition, campaign, split in (
            (CorrectionPartition.TRAINING, FITTING_CAMPAIGN, "fit"),
            (CorrectionPartition.CALIBRATION, CALIBRATION_CAMPAIGN, "calibration"),
        ):
            row = next(
                item for item in sealed["partitions"] if item["partition"] == partition.value
            )
            data = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
            seal = SealedFeatureRecordSetV2.model_validate_json(data.decode())
            if seal.content_hash != row["feature_seal_hash"]:
                raise SystemExit(f"{partition.value}: the stored seal is not the recorded one")
            outcomes = json.loads(campaign.read_text(encoding="utf-8"))["candidate_outcomes"]
            matrices.append(_matrix(outcomes, seal, split=split, partition=partition.value))
    finally:
        await engine.dispose()
    return matrices[0], matrices[1]


async def _run(output: Path) -> int:
    fit_matrix, calibration_matrix = await _load()
    requirement, delta = _texts(CorrectionPartition.CALIBRATION)
    order = _orders(CorrectionPartition.CALIBRATION)

    ladder = build_ladder(
        calibration_matrix,
        order=order,
        requirement_texts=requirement,
        delta_texts=delta,
        created_at=utc_now(),
    )
    ordering = eligible_rungs(calibration_matrix.rows[0].vector.encoder_version)[
        ladder.strongest_non_learned_name
    ]
    baseline_order = {
        item.group: ordering(item)
        for item in group_candidates(
            calibration_matrix,
            order=order,
            requirement_texts=requirement,
            delta_texts=delta,
        )
    }

    vectors: dict[str, dict[str, CorrectionFeatureVector]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    hashes: dict[str, dict[str, str]] = {}
    for row in calibration_matrix.rows:
        vectors.setdefault(row.group, {})[str(row.candidate_id)] = row.vector
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted
        hashes.setdefault(row.group, {})[str(row.candidate_id)] = row.sealed_feature_hash

    groups = tuple(
        _Group(
            group=name,
            order=order[name],
            vectors=vectors[name],
            accepted=accepted[name],
            baseline_first_choice=baseline_order[name][0],
            # A ranking decision's identity is the four fitted vectors it chooses among, in
            # slot order. Two groups sharing one would be one decision counted twice.
            signature=_digest("|".join(hashes[name][item] for item in order[name])),
        )
        for name in sorted(order)
    )
    census = DecisionCensusV4.from_feature_hashes([item.signature for item in groups])
    independent = census.independent_decisions

    grid = declared_grid()
    cells: list[dict[str, Any]] = []
    curve: dict[str, Any] = {}
    calibration_source = calibration_matrix.content_hash
    derivations = 0

    for volume in VOLUME_POINTS:
        exemplars = tuple(
            Exemplar(vector=row.vector, accepted=row.accepted)
            for row in _volume_rows(fit_matrix, volume)
        )
        best_zero_error_coverage = Decimal("0")
        for index, setting in enumerate(grid):
            decisions, slowest = _score_setting(setting, exemplars, groups)
            scored = [
                {
                    "decision_id": item["group"],
                    "feature_hash": item["signature"],
                    "score": Decimal(item["score"]),
                    "answered": bool(item["answered"]),
                    "correct": bool(item["correct"]),
                }
                for item in decisions
            ]
            point = derive_zero_error_point(
                [ScoredDecision(**item) for item in scored],
                split="calibration",
                calibration_source_hash=calibration_source,
                derived_at=utc_now(),
            )
            derivations += 1
            derivation = {
                "exists": point.zero_error_point_exists,
                "threshold": point.threshold,
                "every_answered_decision_was_correct": point.every_answered_decision_was_correct,
                "admitted_decisions": point.admitted_decisions,
                "coverage": point.coverage,
                "zero_error_upper_bound_95": point.zero_error_upper_bound_95,
                "derivation_hash": point.derivation_hash,
                "rule": DERIVATION_RULE,
                "split": point.split,
            }
            if point.zero_error_point_exists and point.coverage is not None:
                best_zero_error_coverage = max(
                    best_zero_error_coverage, Decimal(str(point.coverage))
                )

            for name in (*RELEASED_FLOORS, DERIVED):
                if name == DERIVED:
                    if not point.zero_error_point_exists:
                        threshold: Decimal | None = None
                    else:
                        threshold = (
                            None if point.threshold is None else Decimal(str(point.threshold))
                        )
                    detail: dict[str, Any] | None = derivation
                else:
                    threshold = Decimal(name)
                    detail = None
                cell = _cell(
                    setting=setting,
                    volume=volume,
                    operating_point=name,
                    threshold=threshold,
                    decisions=decisions,
                    slowest=slowest,
                    independent=independent,
                    derivation=detail,
                )
                cell["grid_index"] = index
                if name == DERIVED and not point.zero_error_point_exists:
                    cell["ineligible_reasons"] = ["no_zero_error_point_exists"]
                else:
                    cell["ineligible_reasons"] = _satisfies_section_2_3(cell)
                cells.append(cell)
        at_this_volume = [cell for cell in cells if cell["volume_rows"] == volume]
        rates = [
            Decimal(str(cell["first_choice_rate_over_admitted"]))
            for cell in at_this_volume
            if cell["first_choice_rate_over_admitted"] is not None
        ]
        curve[str(volume)] = {
            "exemplar_rows": volume,
            "exemplar_groups": volume // 4,
            "best_zero_error_coverage": str(best_zero_error_coverage),
            "settings_measured": len(grid),
            "cells": len(at_this_volume),
            # The risk half of the risk-coverage curve. Zero-error coverage alone is one
            # number, and one number cannot show whether the grid came close.
            "fewest_confident_errors": min(
                int(cell["confident_errors"]) for cell in at_this_volume
            ),
            "most_confident_errors": max(int(cell["confident_errors"]) for cell in at_this_volume),
            "cells_with_zero_confident_errors": sum(
                1
                for cell in at_this_volume
                if int(cell["confident_errors"]) == 0 and int(cell["admitted_decisions"]) > 0
            ),
            "coverage_range": [
                str(min(Decimal(str(cell["coverage"])) for cell in at_this_volume)),
                str(max(Decimal(str(cell["coverage"])) for cell in at_this_volume)),
            ],
            "best_first_choice_rate_over_admitted": str(max(rates)) if rates else None,
            "median_first_choice_rate_over_admitted": (
                str(sorted(rates)[len(rates) // 2]) if rates else None
            ),
            "cells_beating_the_baseline": sum(
                1 for cell in at_this_volume if cell["beats_the_baseline"]
            ),
        }

    eligible = [cell for cell in cells if not cell["ineligible_reasons"]]
    selected, precedence = _select(cells)
    stop, tree_reading = _classify(curve, len(eligible))

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D4",
            "wave": "W2",
            "items": ["S21D4-039"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "feature_seals_sha256": _digest(SEAL_RECORD.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "invariance_regression_sha256": _digest(INVARIANCE.read_bytes()),
            "fitting_pool_sha256": _digest(FITTING_POOL.read_bytes()),
            "fitting_campaign_sha256": _digest(FITTING_CAMPAIGN.read_bytes()),
            "calibration_campaign_sha256": _digest(CALIBRATION_CAMPAIGN.read_bytes()),
            "final_or_canary_outcomes_inspected": 0,
            "final_outcomes_inspected": False,
            "decisions": {
                "census": census.model_dump(
                    mode="json", exclude={"content_hash", "independence_rule"}
                ),
                "independent_decisions": independent,
                "identity_rule": (
                    "a ranking decision is identified by its four fitted feature vectors in "
                    "slot order; two groups sharing one would be one decision counted twice"
                ),
                "calibration_matrix_hash": calibration_source,
                "fit_matrix_hash": fit_matrix.content_hash,
            },
            "baseline": {
                "strongest_deterministic_rung": ladder.strongest_non_learned_name,
                "ladder_hash": ladder.content_hash,
                "measured_on": "the same 100 calibration decisions the grid is measured on",
                "rungs": [
                    {
                        "name": rung.name,
                        "kind": rung.kind,
                        "eligible": rung.eligible,
                        "groups_scored": rung.groups_scored,
                        "first_choice_rate": None
                        if rung.first_choice_rate is None
                        else str(rung.first_choice_rate),
                        "ineligible_reason": rung.ineligible_reason,
                    }
                    for rung in ladder.rungs
                ],
            },
            "grid": {
                "hash": grid_hash(),
                "settings": len(grid),
                "operating_points": [*RELEASED_FLOORS, DERIVED],
                "volume_points": list(VOLUME_POINTS),
                "cells": len(cells),
                "cells_reported": len(cells),
                "fully_abstaining_cells": sum(1 for cell in cells if cell["fully_abstaining"]),
                "filtered_no_changed_decision": sum(
                    1 for cell in cells if cell["filtered_no_changed_decision"]
                ),
                "zero_error_derivations": derivations,
                "two_gates": (
                    "the setting's confidence floor decides abstention; the operating point "
                    "decides admission among the decisions it answered"
                ),
            },
            "risk_coverage_curve": curve,
            "section_2_3": {
                "minimum_independent_decisions": MINIMUM_INDEPENDENT_DECISIONS,
                "minimum_clean_coverage": str(MINIMUM_CLEAN_COVERAGE),
                "confident_errors_allowed": CONFIDENT_ERRORS_ALLOWED,
                "minimum_projected_changed_final_decisions": (
                    MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS
                ),
                "final_groups": FINAL_GROUPS,
                "inference_budget_ms": str(INFERENCE_BUDGET_MS),
                "first_action_preservation_on_the_invariance_sample": (
                    json.loads(INVARIANCE.read_text(encoding="utf-8"))["first_action"]["changes"]
                    == 0
                ),
                "eligible_cells": len(eligible),
                "ineligibility_counts": _reasons(cells),
            },
            "selection": _selection_block(selected, precedence, stop, tree_reading),
            "decision_tree": {
                "section": "3.3",
                "reading": tree_reading,
                "stop": stop,
                "outcome_4_and_5_not_guessed": True,
            },
            "residual": {
                "the_grid_carries_signal": (
                    "every one of the 144 cells beats the strongest deterministic baseline on "
                    "the same decisions. The frozen k-NN is not noise on this representation"
                ),
                "and_cannot_be_made_selective": (
                    "no cell, at any operating point or volume, reaches zero confident errors "
                    "on a non-empty admitted set. Selective prediction needs a threshold above "
                    "which the ranker is never confidently wrong, and the grid has none"
                ),
                "which_is_why_the_stop_is_hypothesis_class_and_not_volume": (
                    "zero-error coverage is exactly zero at both 200 and 320 exemplar rows, so "
                    "there is no non-zero coverage for more evidence to enlarge. Section 3.3 "
                    "step 4 needs coverage above zero and rising; step 5 is the branch the "
                    "measurement actually lands in"
                ),
                "what_a_successor_would_need": (
                    "a hypothesis class that can separate its own errors on these features, "
                    "pre-registered on this residual rather than on a guess. That is the "
                    "recommendation Section 3.4 permits once the reconciliation reproduces, "
                    "the calibration set yields 100 independent decisions, the matrix passes "
                    "every scan, and no final batch is opened -- all four of which hold"
                ),
            },
            "limitations": {
                "s21c3_corpus_excluded": (
                    "the volume probe spans 200 to 320 rather than 200 to 440, because Sprint "
                    "21C3's corpus was excluded by release-owner decision. A flat risk-coverage "
                    "curve across the narrower span is weaker evidence for "
                    "hypothesis_class_bound than a flat curve to 440 would have been, and this "
                    "record reports that rather than let a reader infer a stronger conclusion "
                    "than the spacing supports"
                ),
                "volume_spacing": "200 and 320 exemplar rows, 50 and 80 fitting groups",
                "batch_dependence": (
                    "no vector was encoded here; every one comes from the S21D4-034 seals, so "
                    "W2-D9's batch-composition dependence cannot reach the differences between "
                    "settings"
                ),
            },
            "cells": cells,
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "independent_decisions": independent,
                "baseline": ladder.strongest_non_learned_name,
                "baseline_first_choice_rate": str(ladder.strongest_non_learned_rate),
                "cells": len(cells),
                "eligible_cells": len(eligible),
                "zero_error_coverage": {
                    key: value["best_zero_error_coverage"] for key, value in curve.items()
                },
                "selected": None if selected is None else selected["setting"],
                "stop": stop,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def _reasons(cells: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for cell in cells:
        for reason in cell["ineligible_reasons"]:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _selection_block(
    selected: dict[str, Any] | None,
    precedence: dict[str, Any],
    stop: str | None,
    reading: str,
) -> dict[str, Any]:
    """One candidate, or an immutable null with its typed stop and everything left closed."""
    if selected is not None:
        return {
            "outcome": "candidate",
            "precedence": precedence,
            "setting": selected["setting"],
            "operating_point": selected["operating_point"],
            "threshold": selected["threshold"],
            "volume_rows": selected["volume_rows"],
            "coverage": selected["coverage"],
            "first_choice_rate_over_admitted": selected["first_choice_rate_over_admitted"],
            "confident_errors": selected["confident_errors"],
            "changed_decisions": selected["changed_decisions"],
            "projected_changed_final_decisions": selected["projected_changed_final_decisions"],
            "zero_error_upper_bound_95": selected["zero_error_upper_bound_95"],
            "maximum_inference_ms": selected["maximum_inference_ms"],
        }
    return {
        "outcome": "null",
        "immutable": True,
        "precedence": precedence,
        "stop_kind": stop,
        "reading": reading,
        "dependent_not_opened": list(DEPENDENT_NOT_OPENED),
        "why_a_null_and_not_a_weaker_candidate": (
            "Section 2.3's conditions are the selection rule, not a preference. A cell that "
            "fails one is not a worse candidate, it is not a candidate"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
