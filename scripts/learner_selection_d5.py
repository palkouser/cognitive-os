#!/usr/bin/env python3
"""S21D5-032 to S21D5-035. Fit the direction, measure the baseline, derive the point, decide.

Four stages, four records, and the stage boundaries are the evidence rather than a convenience:

*`--stage fit` (S21D5-032)* fits `pairwise-contrastive-linear-v1` at 320 and at 720 fitting rows
and stores each direction in the artifact store. It never opens the calibration campaign, which
is what makes "both models sealed before any calibration decision is scored" checkable instead of
asserted -- the later stages reload the stored bytes and refuse if the hash moved.

*`--stage baseline` (S21D5-033)* measures the deterministic ladder on the hundred calibration
decisions, every rung recorded including the ineligible ones. No model is loaded here; the
baseline is a property of the corpus, and measuring it beside the learner is how a learner gets
credit for the corpus's own separability.

*`--stage point` (S21D5-034)* scores the calibration set with each stored direction and derives
the zero-error operating point once per volume, from the calibration split only.

*`--stage select` (S21D5-035)* is a second process. It reloads the directions and the derived
points, re-scores, and re-derives passing the sealed point back, so `derive_zero_error_point`
refuses if this run produced a different threshold. That is the single-derivation rule enforced
across a restart. Then every cell is reported, Section 2.3 decides eligibility, and Section 3.3
decides the ending. There is no path here that asserts a pass.

Two gates, deliberately distinct, because collapsing them is how a selective ranker gets credit
for work it did not do. *The margin floor decides abstention* and runs at zero throughout: the
abstention gate is not searched, because searching it on the certification set is the threshold
search Section 3.4 forbids. *The operating point decides admission*, and it is derived rather
than chosen. Coverage is admitted decisions over independent decisions, and a confident error is
an admitted decision that is wrong.

Nothing here encodes anything. Every vector comes out of the S21D5-025 seals the artifact store
holds, and the two matrices are checked against the hashes S21D5-030's scans passed on. No final,
batch-B or canary body, outcome or manifest is opened.

    set -a && . ./.env.s21d5.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d5.py --stage fit
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d5.py --stage baseline
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d5.py --stage point
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d5.py --stage select
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

from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    RealityCampaignLedger,
)
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    D5_VOLUME_POINTS,
    seal_d5_corpus,
)
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
    Exemplar,
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    FIT_RULE,
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
    fit_pairwise_direction,
)
from cognitive_os.learning.selective_operating_point import (  # noqa: E402
    DERIVATION_RULE,
    OperatingPointV4,
    ScoredDecision,
    derive_zero_error_point,
    zero_error_upper_bound,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SEAL_RECORD = EVIDENCE / "sprint-21d5-feature-seals.json"
FITTING_CAMPAIGN = EVIDENCE / "sprint-21d5-self-play-campaign.json"
CALIBRATION_CAMPAIGN = EVIDENCE / "sprint-21d5-calibration-campaign.json"
SNAPSHOTS = EVIDENCE / "sprint-21d5-snapshots.json"
INVARIANCE = EVIDENCE / "sprint-21d5-invariance-regression.json"
DIRECTION_FIT = EVIDENCE / "sprint-21d5-direction-fit.json"
BASELINE = EVIDENCE / "sprint-21d5-baseline-ladder.json"
OPERATING_POINT = EVIDENCE / "sprint-21d5-operating-point.json"
SELECTION = EVIDENCE / "sprint-21d5-learner-selection.json"

MODEL_MEDIA_TYPE = "application/json"

#: S21D5-011 declared these before any D5 measurement. Whole groups, so a volume point never
#: fits on three of a group's four candidates.
VOLUME_POINTS: tuple[int, ...] = D5_VOLUME_POINTS

#: S21D5-010 froze it, and S21D5-016 forbade re-choosing it.
REGULARIZATION = Decimal("1")

#: The abstention gate at measurement time. Not a setting this wave may move: a margin floor
#: chosen against the calibration decisions would be a threshold searched on the set the
#: selection is certified against.
MARGIN_FLOOR = Decimal("0")

DERIVED = "zero_error"

#: §2.3, verbatim as thresholds.
MINIMUM_INDEPENDENT_DECISIONS = 100
MINIMUM_CLEAN_COVERAGE = Decimal("0.40")
FINAL_GROUPS = 60
MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS = 20
CONFIDENT_ERRORS_ALLOWED = 0
INFERENCE_BUDGET_MS = Decimal("250")

#: §3.3's endings, by name, so a reader is never asked to infer which one fired.
STOP_VOLUME_BOUND = "volume_bound"
STOP_SELECTIVE_MARGIN_BOUND = "selective_margin_bound"
STOP_HYPOTHESIS_CLASS_BOUND = "hypothesis_class_bound"

#: §3.3 says "materially higher" and "at or near zero" and quantifies neither. These make the
#: words operational, and they are derived from the power contract rather than from the
#: measurement: five admitted decisions out of a hundred is 0.05 coverage, and zero errors in
#: five decisions bounds the true error rate at 45%, which certifies nothing anybody would act
#: on. So coverage at or below 0.05 is "near zero", and a volume difference of at least 0.05 --
#: five decisions -- is "material". Every raw number is in the record, so a reader who prefers
#: another reading can apply it without re-running anything.
NEAR_ZERO_COVERAGE = Decimal("0.05")
MATERIAL_COVERAGE_DIFFERENCE = Decimal("0.05")

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
    """The convention every D4 and D5 record shares: hashed bytes are written bytes."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _write(output: Path, evidence: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d5.local first")
    return value


def _services(engine: Any) -> tuple[ArtifactService, RealityCampaignLedger]:
    artifacts = ArtifactService(
        ContentAddressedFilesystem(Path(_require("COGOS_ARTIFACT_ROOT"))),
        PostgresArtifactRepository(engine),
    )
    ledger = RealityCampaignLedger(PostgresEventStore(engine, build_default_event_catalog()))
    return artifacts, ledger


# --------------------------------------------------------------------------- the two matrices


async def _matrix(
    artifacts: ArtifactService,
    ledger: RealityCampaignLedger,
    partition: CorrectionPartition,
    *,
    split: str,
    campaign_path: Path,
) -> FittedMatrix:
    """One matrix, from the sealed vectors and the ledger's labels — never from a report.

    Its content hash is compared against S21D5-030's below. Rebuilding rather than reloading is
    deliberate: a selection that scored rows nobody scanned would be a selection about a
    different matrix, and the hash is what says these are the scanned ones.
    """
    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    row = next(item for item in sealed["partitions"] if item["partition"] == partition.value)
    data = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
    seal = SealedFeatureRecordSetV2.model_validate_json(data.decode())
    if seal.content_hash != row["feature_seal_hash"]:
        raise SystemExit(f"{partition.value}: the stored seal is not the recorded one")

    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    recorded = await ledger.completed_by_identity([UUID(item) for item in campaign["task_run_ids"]])
    outcomes = {
        reference.candidate_id: reference
        for reference in recorded.values()
        if reference.candidate_id is not None
    }
    rows: list[FittedRow] = []
    for item in campaign["candidate_outcomes"]:
        candidate_id = UUID(str(item["candidate_id"]))
        record = seal.record_for(candidate_id)
        outcome = outcomes[candidate_id]
        rows.append(
            FittedRow(
                candidate_id=candidate_id,
                task_id=UUID(str(item["task_id"])),
                group=str(item["group"]),
                partition=partition.value,
                vector=CorrectionFeatureVector(
                    encoder_version=record.encoder_version,
                    values=record.values,
                    embedding=record.embedding,
                ),
                accepted=outcome.hidden_verification_passed,
                sealed_at=seal.sealed_at,
                outcome_at=outcome.occurred_at,
                observation_id=UUID(str(item["observation_id"])),
                sealed_feature_hash=record.feature_vector_hash,
            )
        )
    matrix = FittedMatrix(split=split, rows=tuple(rows))
    expected = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    key = "fit_matrix_hash" if split == "fit" else "calibration_matrix_hash"
    if matrix.content_hash != expected[key]:
        raise SystemExit(
            f"the {split} matrix is not the one S21D5-030 scanned: {matrix.content_hash} "
            f"against {expected[key]}"
        )
    return matrix


def _volume_groups(matrix: FittedMatrix, rows: int) -> tuple[tuple[Exemplar, ...], ...]:
    """The first `rows` fitting rows as whole groups, in sorted group order.

    Whole groups on purpose: fitting on three of a group's four candidates would put the
    fourth's siblings in the fitted set and call the result a volume effect.
    """
    by_group: dict[str, list[FittedRow]] = {}
    for row in matrix.rows:
        by_group.setdefault(row.group, []).append(row)
    taken: list[tuple[Exemplar, ...]] = []
    counted = 0
    for name in sorted(by_group):
        members = sorted(by_group[name], key=lambda item: str(item.candidate_id))
        if counted + len(members) > rows:
            break
        counted += len(members)
        taken.append(tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in members))
    if counted != rows:
        raise SystemExit(f"a {rows}-row volume point does not land on a group boundary")
    return tuple(taken)


# ------------------------------------------------------------------- the calibration decisions


@dataclass(frozen=True, slots=True)
class _Group:
    """One calibration group as a decision: one order, four vectors, four labels."""

    group: str
    order: tuple[str, ...]
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]
    baseline_first_choice: str
    #: The decision's identity for the census: the group's four fitted vectors, in slot order.
    signature: str


def _texts() -> tuple[dict[str, str], dict[str, str]]:
    """Requirement and per-candidate texts, for the lexical rung of the baseline ladder."""
    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    for group in seal_d5_corpus().catalogues[CorrectionPartition.CALIBRATION].groups:
        item = template(group.template_id)
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    return requirement, delta


def _orders() -> dict[str, tuple[str, ...]]:
    return {
        group.repository_group: tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for group in seal_d5_corpus().catalogues[CorrectionPartition.CALIBRATION].groups
    }


def _ladder(matrix: FittedMatrix) -> tuple[Any, dict[str, tuple[str, ...]]]:
    """The deterministic ladder and the order its strongest rung would act on."""
    requirement, delta = _texts()
    order = _orders()
    ladder = build_ladder(
        matrix,
        order=order,
        requirement_texts=requirement,
        delta_texts=delta,
        created_at=utc_now(),
    )
    ordering = eligible_rungs(matrix.rows[0].vector.encoder_version)[
        ladder.strongest_non_learned_name
    ]
    baseline_order = {
        item.group: ordering(item)
        for item in group_candidates(
            matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }
    return ladder, baseline_order


def _decisions(matrix: FittedMatrix) -> tuple[tuple[_Group, ...], Any, DecisionCensusV4]:
    ladder, baseline_order = _ladder(matrix)
    order = _orders()
    vectors: dict[str, dict[str, CorrectionFeatureVector]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    hashes: dict[str, dict[str, str]] = {}
    for row in matrix.rows:
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
    return groups, ladder, census


def _score(
    model: PairwiseContrastiveModel, groups: tuple[_Group, ...]
) -> tuple[list[dict[str, Any]], Decimal]:
    """One direction over every calibration group. Abstention only; admission comes later."""
    ranker = PairwiseContrastiveRanker(model, margin_floor=MARGIN_FLOOR)
    decisions: list[dict[str, Any]] = []
    slowest = Decimal("0")
    for item in groups:
        started = datetime.now(UTC)
        ranking = ranker.rank(item.vectors, baseline_order=item.order)
        elapsed = Decimal(str(round((datetime.now(UTC) - started).total_seconds() * 1000, 3)))
        slowest = max(slowest, elapsed / Decimal(len(item.order)))
        first = ranking.ordered_candidate_ids[0] if not ranking.abstained else None
        decisions.append(
            {
                "group": item.group,
                "signature": item.signature,
                "answered": not ranking.abstained,
                "score": str(ranking.confidence),
                "first_choice": first,
                "correct": bool(first and item.accepted[first]),
                "changed": (not ranking.abstained) and first != item.baseline_first_choice,
                "baseline_correct": item.accepted[item.baseline_first_choice],
            }
        )
    return decisions, slowest


# ------------------------------------------------------------------------- the stored direction


def _model_bytes(model: PairwiseContrastiveModel) -> bytes:
    """Round-trippable bytes. `canonical_bytes` is a hash input, not a serialisation."""
    return json.dumps(
        {
            "hypothesis_class": HYPOTHESIS_CLASS,
            "encoder_version": model.encoder_version,
            "feature_names": list(model.feature_names),
            "weights": list(model.weights),
            "regularization": model.regularization,
            "fitted_group_count": model.fitted_group_count,
            "fitted_pair_count": model.fitted_pair_count,
        },
        indent=1,
        sort_keys=True,
    ).encode("utf-8")


def _model_from_bytes(data: bytes) -> PairwiseContrastiveModel:
    payload = json.loads(data.decode())
    if payload["hypothesis_class"] != HYPOTHESIS_CLASS:
        raise SystemExit(f"stored direction claims {payload['hypothesis_class']}")
    return PairwiseContrastiveModel(
        encoder_version=str(payload["encoder_version"]),
        feature_names=tuple(str(name) for name in payload["feature_names"]),
        weights=tuple(float(weight) for weight in payload["weights"]),
        regularization=str(payload["regularization"]),
        fitted_group_count=int(payload["fitted_group_count"]),
        fitted_pair_count=int(payload["fitted_pair_count"]),
    )


async def _stored_models(
    artifacts: ArtifactService,
) -> dict[int, tuple[PairwiseContrastiveModel, dict[str, Any]]]:
    """Both directions, reloaded from the store and checked against S21D5-032's record."""
    record = json.loads(DIRECTION_FIT.read_text(encoding="utf-8"))
    loaded: dict[int, tuple[PairwiseContrastiveModel, dict[str, Any]]] = {}
    for item in record["models"]:
        data = await artifacts.get_bytes(UUID(str(item["artifact_id"])))
        model = _model_from_bytes(data)
        if model.content_hash() != item["model_hash"]:
            raise SystemExit(
                f"the stored direction at {item['volume_rows']} rows is not the sealed one"
            )
        loaded[int(item["volume_rows"])] = (model, item)
    if sorted(loaded) != sorted(VOLUME_POINTS):
        raise SystemExit(f"S21D5-032 sealed {sorted(loaded)}, not {sorted(VOLUME_POINTS)}")
    return loaded


# ------------------------------------------------------------------------------- S21D5-032


async def _stage_fit(output: Path) -> int:
    """Fit at both volumes and store the bytes. No calibration label is read."""
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    try:
        artifacts, ledger = _services(engine)
        fit_matrix = await _matrix(
            artifacts,
            ledger,
            CorrectionPartition.TRAINING,
            split="fit",
            campaign_path=FITTING_CAMPAIGN,
        )
        models: list[dict[str, Any]] = []
        for volume in VOLUME_POINTS:
            groups = _volume_groups(fit_matrix, volume)
            model = fit_pairwise_direction(groups, regularization=REGULARIZATION)
            # Refit in the same process and compare hashes. It says the solver is deterministic
            # on this machine; it does not say the weights are bit-identical on another BLAS,
            # which is why every consumer reloads the stored bytes instead of refitting.
            again = fit_pairwise_direction(groups, regularization=REGULARIZATION)
            stored = await artifacts.put_bytes(_model_bytes(model), media_type=MODEL_MEDIA_TYPE)
            reloaded = _model_from_bytes(await artifacts.get_bytes(stored.artifact_id))
            magnitudes = sorted(abs(weight) for weight in model.weights)
            models.append(
                {
                    "volume_rows": volume,
                    "volume_groups": volume // 4,
                    "fitted_group_count": model.fitted_group_count,
                    "fitted_pair_count": model.fitted_pair_count,
                    "model_hash": model.content_hash(),
                    "artifact_id": str(stored.artifact_id),
                    "stored_bytes": len(_model_bytes(model)),
                    "weights": len(model.weights),
                    "channels_are_the_encoder_s_fitted_names": (
                        model.feature_names == fit_matrix.rows[0].vector.fitted_names
                    ),
                    "refit_in_process_reproduces_the_hash": (
                        again.content_hash() == model.content_hash()
                    ),
                    "reload_from_the_store_reproduces_the_hash": (
                        reloaded.content_hash() == model.content_hash()
                    ),
                    "largest_absolute_weight": f"{magnitudes[-1]:.6g}",
                    "median_absolute_weight": f"{magnitudes[len(magnitudes) // 2]:.6g}",
                }
            )
    finally:
        await engine.dispose()

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-032"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "fitting_campaign_sha256": _digest(FITTING_CAMPAIGN.read_bytes()),
            "final_outcomes_inspected": False,
            "hypothesis_class": HYPOTHESIS_CLASS,
            "fit_rule": FIT_RULE,
            "regularization": str(REGULARIZATION),
            "regularization_rechosen": False,
            "fit_matrix_hash": json.loads(SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"][
                "fit_matrix_hash"
            ],
            "volume_points": list(VOLUME_POINTS),
            "whole_groups_only": True,
            "calibration_campaign_opened": False,
            "calibration_decisions_scored": 0,
            "why_that_matters": (
                "this stage loads the fitting matrix and nothing else. Both directions are "
                "sealed by content hash here, before any stage has read a calibration label, "
                "which is the chronology S21D5-032 asks for and the reason the later stages "
                "reload these bytes rather than refit"
            ),
            "models": models,
        }
    )
    _write(output, evidence)
    print(
        json.dumps(
            {
                "output": output.name,
                "models": {str(item["volume_rows"]): item["model_hash"][:16] for item in models},
                "fitted_pairs": {
                    str(item["volume_rows"]): item["fitted_pair_count"] for item in models
                },
                "stored_bytes": {str(item["volume_rows"]): item["stored_bytes"] for item in models},
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D5-033


def _rungs(ladder: Any) -> list[dict[str, Any]]:
    return [
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
    ]


async def _stage_baseline(output: Path) -> int:
    """The strongest deterministic rung, measured on the decisions the learner will face."""
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    try:
        artifacts, ledger = _services(engine)
        calibration = await _matrix(
            artifacts,
            ledger,
            CorrectionPartition.CALIBRATION,
            split="calibration",
            campaign_path=CALIBRATION_CAMPAIGN,
        )
    finally:
        await engine.dispose()

    groups, ladder, census = _decisions(calibration)
    rungs = _rungs(ladder)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-033"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "calibration_campaign_sha256": _digest(CALIBRATION_CAMPAIGN.read_bytes()),
            "final_outcomes_inspected": False,
            "calibration_matrix_hash": calibration.content_hash,
            "decisions": {
                "groups": len(groups),
                "census": census.model_dump(
                    mode="json", exclude={"content_hash", "independence_rule"}
                ),
                "independent_decisions": census.independent_decisions,
            },
            "ladder": {
                "hash": ladder.content_hash,
                "rungs_declared": len(rungs),
                "rungs_eligible": sum(1 for rung in rungs if rung["eligible"]),
                "rungs_ineligible": sum(1 for rung in rungs if not rung["eligible"]),
                "strongest_deterministic_rung": ladder.strongest_non_learned_name,
                "strongest_deterministic_rate": str(ladder.strongest_non_learned_rate),
                "measured_on": "the same calibration decisions the direction is measured on",
                "no_model_loaded": True,
                "rungs": rungs,
            },
            "why_every_rung_including_the_ineligible_ones": (
                "the selection rule compares the learner against the strongest deterministic "
                "baseline, and 'strongest' is only meaningful if the weaker rungs are on the "
                "record too. An ineligible rung is recorded with the reason it is ineligible, "
                "so a reader can see that the comparison was not narrowed to a rung the "
                "learner happens to beat"
            ),
        }
    )
    _write(output, evidence)
    print(
        json.dumps(
            {
                "output": output.name,
                "strongest_rung": ladder.strongest_non_learned_name,
                "strongest_rate": str(ladder.strongest_non_learned_rate),
                "rungs": len(rungs),
                "eligible_rungs": sum(1 for rung in rungs if rung["eligible"]),
                "independent_decisions": census.independent_decisions,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D5-034


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


def _point_record(point: OperatingPointV4) -> dict[str, Any]:
    return {
        "exists": point.zero_error_point_exists,
        "threshold": point.threshold,
        "every_answered_decision_was_correct": point.every_answered_decision_was_correct,
        "admitted_decisions": point.admitted_decisions,
        "coverage": point.coverage,
        "zero_error_upper_bound_95": point.zero_error_upper_bound_95,
        "derivation_hash": point.derivation_hash,
        "split": point.split,
        "calibration_source_hash": point.calibration_source_hash,
        "census": point.census.model_dump(mode="json", exclude={"content_hash"}),
        "derived_at": point.derived_at.isoformat(),
        "canonical": point.model_dump(mode="json"),
    }


async def _calibration_and_models(
    engine: Any,
) -> tuple[FittedMatrix, tuple[_Group, ...], Any, DecisionCensusV4, dict[int, Any]]:
    artifacts, ledger = _services(engine)
    calibration = await _matrix(
        artifacts,
        ledger,
        CorrectionPartition.CALIBRATION,
        split="calibration",
        campaign_path=CALIBRATION_CAMPAIGN,
    )
    models = await _stored_models(artifacts)
    groups, ladder, census = _decisions(calibration)
    return calibration, groups, ladder, census, models


async def _stage_point(output: Path) -> int:
    """Derive the zero-error point once per volume, from the calibration split only."""
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    try:
        calibration, groups, _, census, models = await _calibration_and_models(engine)
    finally:
        await engine.dispose()

    derivations: list[dict[str, Any]] = []
    for volume in VOLUME_POINTS:
        model, sealed = models[volume]
        decisions, slowest = _score(model, groups)
        point = derive_zero_error_point(
            _scored(decisions),
            split="calibration",
            calibration_source_hash=calibration.content_hash,
            derived_at=utc_now(),
        )
        derivations.append(
            {
                "volume_rows": volume,
                "model_hash": sealed["model_hash"],
                "model_artifact_id": sealed["artifact_id"],
                "answered_decisions": sum(1 for item in decisions if item["answered"]),
                "maximum_inference_ms_per_candidate": str(slowest),
                "point": _point_record(point),
            }
        )

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-034"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "direction_fit_sha256": _digest(DIRECTION_FIT.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "calibration_campaign_sha256": _digest(CALIBRATION_CAMPAIGN.read_bytes()),
            "final_outcomes_inspected": False,
            "derivation_rule": DERIVATION_RULE,
            "split": "calibration",
            "calibration_matrix_hash": calibration.content_hash,
            "independent_decisions": census.independent_decisions,
            "margin_floor_at_measurement": str(MARGIN_FLOOR),
            "derivations": derivations,
            "single_derivation": {
                "derived_here": len(derivations),
                "one_per_volume": True,
                "why_two_derivations_are_not_two_thresholds": (
                    "the rule is one derivation per (model, calibration split) pair. Two "
                    "volumes are two models, so each derives its own point once; neither is a "
                    "second attempt at the other's"
                ),
                "enforced_across_restart_by": (
                    "S21D5-035, a separate process, which reloads these derivations and passes "
                    "each back to derive_zero_error_point as `previous`; a different threshold "
                    "raises OperatingPointError there rather than being written here"
                ),
            },
        }
    )
    _write(output, evidence)
    print(
        json.dumps(
            {
                "output": output.name,
                "points": {
                    str(item["volume_rows"]): {
                        "exists": item["point"]["exists"],
                        "threshold": item["point"]["threshold"],
                        "admitted": item["point"]["admitted_decisions"],
                        "coverage": item["point"]["coverage"],
                    }
                    for item in derivations
                },
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D5-035


def _cell(
    *,
    volume: int,
    operating_point: str,
    threshold: Decimal | None,
    decisions: list[dict[str, Any]],
    slowest: Decimal,
    independent: int,
    baseline_rate: Decimal,
    derivation: dict[str, Any] | None,
) -> dict[str, Any]:
    """One (volume, operating point) cell, with every denominator named."""
    answered = [item for item in decisions if item["answered"]]
    admitted = [
        item for item in answered if threshold is None or Decimal(str(item["score"])) > threshold
    ]
    errors = [item for item in admitted if not item["correct"]]
    changed = [item for item in admitted if item["changed"]]
    coverage = Decimal(len(admitted)) / Decimal(independent)
    first_choice_rate = (
        Decimal(len(admitted) - len(errors)) / Decimal(len(admitted)) if admitted else None
    )
    projected = (
        (Decimal(len(changed)) / Decimal(len(admitted)) * FINAL_GROUPS) if admitted else Decimal(0)
    )
    return {
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


def _satisfies_section_2_3(cell: dict[str, Any], *, first_action_preserved: bool) -> list[str]:
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
    if not first_action_preserved:
        reasons.append("first_action_not_preserved_on_the_invariance_sample")
    return reasons


def _sweep(
    decisions: list[dict[str, Any]], *, independent: int, baseline_rate: Decimal
) -> list[dict[str, Any]]:
    """The whole risk-coverage curve: every distinct margin, reported, none of them selectable.

    This is the deliverable §3.3 step 4 names. It is not a grid: no point here may be chosen,
    because choosing a threshold on the certification set is the search §3.4 forbids. Only the
    derived zero-error point is a cell.
    """
    answered = [item for item in decisions if item["answered"]]
    thresholds = sorted({Decimal(str(item["score"])) for item in answered}, reverse=True)
    points: list[dict[str, Any]] = []
    for threshold in thresholds:
        admitted = [item for item in answered if Decimal(str(item["score"])) >= threshold]
        errors = [item for item in admitted if not item["correct"]]
        changed = [item for item in admitted if item["changed"]]
        points.append(
            {
                "threshold": str(threshold),
                "admitted_decisions": len(admitted),
                "confident_errors": len(errors),
                "coverage": str(Decimal(len(admitted)) / Decimal(independent)),
                "first_choice_rate_over_admitted": str(
                    Decimal(len(admitted) - len(errors)) / Decimal(len(admitted))
                ),
                "baseline_first_choice_rate": str(baseline_rate),
                "changed_decisions": len(changed),
                "selectable": False,
            }
        )
    return points


def _classify(
    curve: dict[str, Any], *, eligible: int, beats_baseline_anywhere: bool
) -> tuple[str | None, str]:
    """§3.3's tree. Four endings, and the record must not guess between them."""
    at_low = Decimal(str(curve[str(VOLUME_POINTS[0])]["zero_error_coverage"]))
    at_high = Decimal(str(curve[str(VOLUME_POINTS[-1])]["zero_error_coverage"]))
    if eligible:
        return None, (
            "step 3: a volume reaches zero confident errors on at least 100 independent "
            "decisions at coverage at least 0.40, above the baseline, projecting at least 20 "
            "changed final decisions, so selection proceeds"
        )
    if max(at_low, at_high) <= NEAR_ZERO_COVERAGE:
        return STOP_HYPOTHESIS_CLASS_BOUND, (
            f"step 6: zero-error coverage is at or near zero at both volumes ({at_low} at "
            f"{VOLUME_POINTS[0]} rows and {at_high} at {VOLUME_POINTS[-1]}, against a near-zero "
            f"reading of {NEAR_ZERO_COVERAGE}). This contradicts the spent-evidence diagnostic, "
            "and the record says so in those words: the estimate did not transfer to a fresh "
            "corpus, and the next question is why the authored distributions differ, not which "
            "class comes third"
        )
    if at_high - at_low >= MATERIAL_COVERAGE_DIFFERENCE:
        return STOP_VOLUME_BOUND, (
            f"step 4: zero-error coverage is above zero and below 0.40 at {VOLUME_POINTS[-1]} "
            f"rows ({at_high}) and materially higher there than at {VOLUME_POINTS[0]} "
            f"({at_low}), so the residual is evidence volume and the yield curve across the "
            "2.25x span is the deliverable"
        )
    return STOP_SELECTIVE_MARGIN_BOUND, (
        f"step 5: zero-error coverage is above zero, below 0.40, and flat across the two "
        f"volumes ({at_low} at {VOLUME_POINTS[0]} rows, {at_high} at {VOLUME_POINTS[-1]}). The "
        "direction ranks and the margin cannot certify enough of what it ranks, so the "
        "successor pre-registers a different confidence construction over the same ranker"
        + (
            ""
            if beats_baseline_anywhere
            else ". Step 5's wording assumes the first-choice rate stays above the baseline, "
            "and at the derived point it does not; the coverage shape is still step 5's and "
            "the premise is recorded here rather than smoothed over"
        )
    )


def _selection_block(
    selected: dict[str, Any] | None, stop: str | None, reading: str
) -> dict[str, Any]:
    """One candidate, or an immutable null with its typed stop and everything left closed."""
    if selected is not None:
        return {
            "outcome": "candidate",
            "hypothesis_class": HYPOTHESIS_CLASS,
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
        "stop_kind": stop,
        "reading": reading,
        "dependent_not_opened": list(DEPENDENT_NOT_OPENED),
        "why_a_null_and_not_a_weaker_candidate": (
            "Section 2.3's conditions are the selection rule, not a preference. A cell that "
            "fails one is not a worse candidate, it is not a candidate"
        ),
    }


async def _stage_select(output: Path) -> int:
    engine = create_postgres_engine(_require("COGOS_DATABASE_URL"))
    try:
        calibration, groups, ladder, census, models = await _calibration_and_models(engine)
    finally:
        await engine.dispose()

    independent = census.independent_decisions
    baseline_rate = Decimal(
        sum(1 for item in groups if item.accepted[item.baseline_first_choice])
    ) / Decimal(independent)
    invariance = json.loads(INVARIANCE.read_text(encoding="utf-8"))
    first_action_preserved = (
        int(invariance["first_action"]["changes"]) == 0
        and int(invariance["independence"]["vectors_changed"]) == 0
    )
    sealed_points = {
        int(item["volume_rows"]): item
        for item in json.loads(OPERATING_POINT.read_text(encoding="utf-8"))["derivations"]
    }

    cells: list[dict[str, Any]] = []
    curve: dict[str, Any] = {}
    reproduced = 0
    for volume in VOLUME_POINTS:
        model, sealed = models[volume]
        decisions, slowest = _score(model, groups)
        previous = OperatingPointV4.model_validate(sealed_points[volume]["point"]["canonical"])
        # The single-derivation rule across a restart: a different threshold raises here.
        point = derive_zero_error_point(
            _scored(decisions),
            split="calibration",
            calibration_source_hash=calibration.content_hash,
            derived_at=utc_now(),
            previous=previous,
        )
        reproduced += 1
        derivation = _point_record(point)
        derivation.pop("canonical")
        threshold = (
            None
            if not point.zero_error_point_exists or point.threshold is None
            else Decimal(str(point.threshold))
        )
        cell = _cell(
            volume=volume,
            operating_point=DERIVED,
            threshold=threshold,
            decisions=decisions,
            slowest=slowest,
            independent=independent,
            baseline_rate=baseline_rate,
            derivation=derivation,
        )
        cell["model_hash"] = sealed["model_hash"]
        if not point.zero_error_point_exists:
            cell["ineligible_reasons"] = ["no_zero_error_point_exists"]
        else:
            cell["ineligible_reasons"] = _satisfies_section_2_3(
                cell, first_action_preserved=first_action_preserved
            )
        cells.append(cell)

        sweep = _sweep(decisions, independent=independent, baseline_rate=baseline_rate)
        answered = [item for item in decisions if item["answered"]]
        rates = [Decimal(str(item["first_choice_rate_over_admitted"])) for item in sweep]
        curve[str(volume)] = {
            "exemplar_rows": volume,
            "exemplar_groups": volume // 4,
            "model_hash": sealed["model_hash"],
            "fitted_pair_count": sealed["fitted_pair_count"],
            "zero_error_coverage": cell["coverage"] if point.zero_error_point_exists else "0",
            "zero_error_threshold": cell["threshold"],
            "answered_decisions": len(answered),
            "first_choice_rate_over_all_answered": str(
                Decimal(sum(1 for item in answered if item["correct"])) / Decimal(len(answered))
            )
            if answered
            else None,
            "baseline_first_choice_rate": str(baseline_rate),
            "changed_decisions_over_all_answered": sum(1 for item in answered if item["changed"]),
            "confident_errors_at_the_derived_point": cell["confident_errors"],
            "errors_among_all_answered": sum(1 for item in answered if not item["correct"]),
            "sweep_points": len(sweep),
            "best_first_choice_rate_over_admitted": str(max(rates)) if rates else None,
            "deepest_error_free_prefix_by_margin": max(
                (
                    int(item["admitted_decisions"])
                    for item in sweep
                    if int(item["confident_errors"]) == 0
                ),
                default=0,
            ),
            "sweep": sweep,
        }

    eligible = [cell for cell in cells if not cell["ineligible_reasons"]]
    beats_baseline_anywhere = any(cell["beats_the_baseline"] for cell in cells)
    stop, reading = _classify(
        curve, eligible=len(eligible), beats_baseline_anywhere=beats_baseline_anywhere
    )
    selected = eligible[0] if eligible else None

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-035"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "invariance_regression_sha256": _digest(INVARIANCE.read_bytes()),
            "direction_fit_sha256": _digest(DIRECTION_FIT.read_bytes()),
            "baseline_ladder_sha256": _digest(BASELINE.read_bytes()),
            "operating_point_sha256": _digest(OPERATING_POINT.read_bytes()),
            "fitting_campaign_sha256": _digest(FITTING_CAMPAIGN.read_bytes()),
            "calibration_campaign_sha256": _digest(CALIBRATION_CAMPAIGN.read_bytes()),
            "final_or_canary_outcomes_inspected": 0,
            "final_outcomes_inspected": False,
            "hypothesis_class": HYPOTHESIS_CLASS,
            "decisions": {
                "census": census.model_dump(
                    mode="json", exclude={"content_hash", "independence_rule"}
                ),
                "independent_decisions": independent,
                "identity_rule": (
                    "a ranking decision is identified by its four fitted feature vectors in "
                    "slot order; two groups sharing one would be one decision counted twice"
                ),
                "calibration_matrix_hash": calibration.content_hash,
                "matrices_are_the_scanned_ones": True,
            },
            "baseline": {
                "strongest_deterministic_rung": ladder.strongest_non_learned_name,
                "ladder_hash": ladder.content_hash,
                "first_choice_rate": str(baseline_rate),
                "measured_on": "the same 100 calibration decisions the direction is measured on",
                "record": "sprint-21d5-baseline-ladder.json",
                "rungs": _rungs(ladder),
            },
            "two_gates": {
                "abstention": (
                    f"the margin floor, held at {MARGIN_FLOOR} throughout. It is not searched: "
                    "a floor chosen against these decisions would be a threshold fitted to the "
                    "certification set"
                ),
                "admission": (
                    "the derived zero-error operating point, one per volume, derived in "
                    "S21D5-034 and reproduced here across a process restart"
                ),
                "why_d4_s_released_floors_are_absent": (
                    "0.55 and 0.70 are proportions of a k-NN neighbourhood's acceptance mass. "
                    "A projection margin is not a proportion and has no upper bound of one, so "
                    "carrying those numbers across would compare two different quantities and "
                    "call the result a comparator"
                ),
            },
            "single_derivation_across_restart": {
                "derivations_reproduced": reproduced,
                "how": (
                    "each sealed OperatingPointV4 from S21D5-034 is passed back to "
                    "derive_zero_error_point as `previous` in this separate process; a "
                    "different derivation hash raises OperatingPointError instead of writing "
                    "a second threshold"
                ),
                "sealed_derivation_hashes": {
                    str(volume): sealed_points[volume]["point"]["derivation_hash"]
                    for volume in VOLUME_POINTS
                },
            },
            "grid": {
                "selectable_cells": len(cells),
                "cells_reported": len(cells),
                "operating_points": [DERIVED],
                "volume_points": list(VOLUME_POINTS),
                "fully_abstaining_cells": sum(1 for cell in cells if cell["fully_abstaining"]),
                "filtered_no_changed_decision": sum(
                    1 for cell in cells if cell["filtered_no_changed_decision"]
                ),
                "sweep_points_reported": sum(
                    int(curve[str(volume)]["sweep_points"]) for volume in VOLUME_POINTS
                ),
                "why_the_grid_is_two_cells_and_not_a_search": (
                    "D4 crossed a pre-registered 24-setting k-NN grid with three operating "
                    "points. Revision 5 pre-registers one class, one regulariser and one "
                    "confidence, so the only free coordinate is the volume point. Everything "
                    "else a reader might want to see is in the sweep, reported and not "
                    "selectable"
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
                "first_action_preservation_on_the_invariance_sample": first_action_preserved,
                "eligible_cells": len(eligible),
                "ineligibility_counts": _reasons(cells),
                "thresholds_changed": 0,
            },
            "selection": _selection_block(selected, stop, reading),
            "decision_tree": {
                "section": "3.3",
                "reading": reading,
                "stop": stop,
                "near_zero_coverage_reading": str(NEAR_ZERO_COVERAGE),
                "material_coverage_difference": str(MATERIAL_COVERAGE_DIFFERENCE),
                "why_those_two_numbers": (
                    "§3.3 says 'materially higher' and 'at or near zero' and quantifies "
                    "neither. Both readings here come from the power contract, not from the "
                    "measurement: five admitted decisions of a hundred is 0.05 coverage, and "
                    "zero errors in five decisions bounds the true error rate at 45%, which "
                    "certifies nothing. Every raw number is in this record, so another reading "
                    "can be applied without re-running anything"
                ),
                "endings_are_four_different_sprints": True,
            },
            "cells": cells,
        }
    )
    _write(output, evidence)
    print(
        json.dumps(
            {
                "output": output.name,
                "independent_decisions": independent,
                "baseline": ladder.strongest_non_learned_name,
                "baseline_first_choice_rate": str(baseline_rate),
                "zero_error_coverage": {
                    key: value["zero_error_coverage"] for key, value in curve.items()
                },
                "first_choice_rate_over_all_answered": {
                    key: value["first_choice_rate_over_all_answered"]
                    for key, value in curve.items()
                },
                "cells": len(cells),
                "eligible_cells": len(eligible),
                "selected": None if selected is None else selected["volume_rows"],
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


_STAGES = {
    "fit": (_stage_fit, DIRECTION_FIT),
    "baseline": (_stage_baseline, BASELINE),
    "point": (_stage_point, OPERATING_POINT),
    "select": (_stage_select, SELECTION),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=sorted(_STAGES), required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    stage, default = _STAGES[arguments.stage]
    return asyncio.run(stage(arguments.output or default))


if __name__ == "__main__":
    raise SystemExit(main())
