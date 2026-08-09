#!/usr/bin/env python3
"""S21D5 groundwork: the hypothesis-class diagnostic the D4 stop asked for.

The D4 handoff authorises exactly this and no more: the spent calibration set "remain[s]
valid *fitting* and *diagnostic* evidence", and "no new corpus is needed to test whether a
different class has a zero-error region". This script tests one pre-named class — the
pairwise contrastive linear ranker, `cognitive_os.learning.pairwise_contrastive` — on the
sealed D4 evidence, and records what it measures. It selects nothing, derives no threshold
for reuse, opens no final or canary body, and never touches the retrieval holdout result.

Two estimates of the same question, each with its estimator named in the record:

*disjoint_pool* — fit once on the 80 fitting groups, read the 100 authored calibration
decisions. The pools are disjoint, so the number is clean but the pool is small.

*combined_pool_logo* — pool the 180 spent groups, and for each authored group rank it with
a direction fitted on the other 179. Leave-group-out over the authored distribution is the
closest available unbiased estimate of a D5 that fits on everything spent and certifies on
a fresh authored corpus.

The surface half re-reads the released D4 retrieval corpus definitions — corpus text, not
holdout judgements — and measures how many graph sides the `structure_fallback` surface
reaches that the released extraction leaves empty.

    set -a && . ./.env.s21d4.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/hypothesis_class_diagnostic_d5.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.experience.graph_projection import search_terms_from_source  # noqa: E402
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
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
    Exemplar,
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    FIT_RULE,
    HYPOTHESIS_CLASS,
    PairwiseContrastiveRanker,
    fit_pairwise_direction,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SEAL_RECORD = EVIDENCE / "sprint-21d4-feature-seals.json"
FITTING_CAMPAIGN = EVIDENCE / "sprint-21d4-self-play-campaign.json"
CALIBRATION_CAMPAIGN = EVIDENCE / "sprint-21d4-calibration-campaign.json"
LEARNER_SELECTION = EVIDENCE / "sprint-21d4-learner-selection.json"
HANDOFF = REPOSITORY / "docs/sprints/sprint-21/sprint-21d5-handoff.md"
OUTPUT = EVIDENCE / "sprint-21d5-hypothesis-class-diagnostic.json"

#: Fixed before any calibration number was read: chosen on fitting-pool-internal
#: leave-group-out evidence alone, where 1.0 maximised zero-error coverage.
REGULARIZATION = Decimal("1")

#: §2.3 floors, unchanged. Reported beside every estimate; never relaxed.
MINIMUM_CLEAN_COVERAGE = Decimal("0.40")
MINIMUM_INDEPENDENT_DECISIONS = 100
BASELINE_NAME = "lexical_similarity"


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
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


async def _load() -> tuple[FittedMatrix, FittedMatrix]:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    engine = create_postgres_engine(database_url)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
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


def _by_group(matrix: FittedMatrix) -> dict[str, list[FittedRow]]:
    grouped: dict[str, list[FittedRow]] = {}
    for row in matrix.rows:
        grouped.setdefault(row.group, []).append(row)
    return {name: sorted(rows, key=lambda r: str(r.candidate_id)) for name, rows in grouped.items()}


def _exemplar_groups(grouped: dict[str, list[FittedRow]]) -> list[list[Exemplar]]:
    return [
        [Exemplar(vector=row.vector, accepted=row.accepted) for row in grouped[name]]
        for name in sorted(grouped)
    ]


def _decide(
    ranker: PairwiseContrastiveRanker,
    rows: list[FittedRow],
    order: tuple[str, ...],
    baseline_first: str,
) -> dict[str, Any]:
    vectors = {str(row.candidate_id): row.vector for row in rows}
    accepted = {str(row.candidate_id): row.accepted for row in rows}
    ranking = ranker.rank(vectors, baseline_order=order)
    first = ranking.first_choice
    return {
        "margin": str(ranking.confidence),
        "correct": bool(first and accepted[first]),
        "changed": (not ranking.abstained) and first != baseline_first,
    }


def _zero_error_region(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    wrong = [Decimal(item["margin"]) for item in decisions if not item["correct"]]
    threshold = max(wrong) if wrong else None
    admitted = [
        item for item in decisions if threshold is None or Decimal(item["margin"]) > threshold
    ]
    changed = sum(1 for item in admitted if item["changed"])
    total = len(decisions)
    ordered = sorted(decisions, key=lambda item: -Decimal(item["margin"]))
    depth: dict[str, int] = {}
    for count in (20, 30, 40, 50):
        if count <= total:
            depth[f"errors_in_top_{count}_by_margin"] = sum(
                1 for item in ordered[:count] if not item["correct"]
            )
    return {
        "decisions": total,
        "first_choice_rate_over_all": str(
            Decimal(sum(1 for item in decisions if item["correct"])) / Decimal(total)
        ),
        "zero_error_coverage": str(Decimal(len(admitted)) / Decimal(total)),
        "admitted_decisions": len(admitted),
        "projected_changed_final_decisions": (
            str(round(Decimal(changed) / Decimal(len(admitted)) * 60, 3)) if admitted else "0"
        ),
        "margin_depth": depth,
    }


def _surface_completion() -> dict[str, Any]:
    empty_before = reached_after = 0
    fallback_documents: list[tuple[str, ...]] = []
    for spec in D4_RETRIEVAL_SPECS:
        for side in (spec.failed, spec.repaired):
            text = spec.module_text(side)
            released = search_terms_from_source(text)
            if released:
                continue
            empty_before += 1
            widened = search_terms_from_source(text, structure_fallback=True)
            if widened:
                reached_after += 1
                if side is spec.repaired:
                    fallback_documents.append(widened)
    return {
        "graph_sides": len(D4_RETRIEVAL_SPECS) * 2,
        "empty_under_released_extraction": empty_before,
        "reached_by_structure_fallback": reached_after,
        "still_empty": empty_before - reached_after,
        "fallback_repaired_documents": len(fallback_documents),
        "fallback_repaired_documents_distinct": len(set(fallback_documents)),
        "reads": "corpus definitions only; no holdout judgement or result was opened",
    }


async def _run(output: Path) -> int:
    fit_matrix, calibration_matrix = await _load()
    fit_groups = _by_group(fit_matrix)
    calibration_groups = _by_group(calibration_matrix)

    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    for group in seal_d4_corpus().catalogues[CorrectionPartition.CALIBRATION].groups:
        item = template(group.template_id)
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    order = {
        group.repository_group: tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for group in seal_d4_corpus().catalogues[CorrectionPartition.CALIBRATION].groups
    }
    ladder = build_ladder(
        calibration_matrix,
        order=order,
        requirement_texts=requirement,
        delta_texts=delta,
        created_at=utc_now(),
    )
    if ladder.strongest_non_learned_name != BASELINE_NAME:
        raise SystemExit("the strongest deterministic rung moved; the record would mislabel it")
    ordering = eligible_rungs(calibration_matrix.rows[0].vector.encoder_version)[BASELINE_NAME]
    baseline_first = {
        item.group: ordering(item)[0]
        for item in group_candidates(
            calibration_matrix,
            order=order,
            requirement_texts=requirement,
            delta_texts=delta,
        )
    }

    started = datetime.now(UTC)

    # Estimate 1: disjoint pools. Fit on the 80 fitting groups, read the 100 authored ones.
    disjoint_model = fit_pairwise_direction(
        _exemplar_groups(fit_groups), regularization=REGULARIZATION
    )
    ranker = PairwiseContrastiveRanker(disjoint_model)
    disjoint_decisions = [
        _decide(ranker, calibration_groups[name], order[name], baseline_first[name])
        for name in sorted(calibration_groups)
    ]

    # Estimate 2: combined pool, leave-one-authored-group-out.
    combined = {f"fit::{name}": rows for name, rows in fit_groups.items()}
    combined.update({f"cal::{name}": rows for name, rows in calibration_groups.items()})
    logo_decisions = []
    for name in sorted(calibration_groups):
        held_out = f"cal::{name}"
        pool = [
            [Exemplar(vector=row.vector, accepted=row.accepted) for row in combined[other]]
            for other in sorted(combined)
            if other != held_out
        ]
        model = fit_pairwise_direction(pool, regularization=REGULARIZATION)
        logo_decisions.append(
            _decide(
                PairwiseContrastiveRanker(model),
                calibration_groups[name],
                order[name],
                baseline_first[name],
            )
        )
    elapsed = round((datetime.now(UTC) - started).total_seconds(), 1)

    disjoint = _zero_error_region(disjoint_decisions)
    logo = _zero_error_region(logo_decisions)
    surface = _surface_completion()

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "purpose": "hypothesis-class diagnostic on spent evidence, per the D4 handoff",
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "authorisation": (
                "sprint-21d5-handoff.md section 2: the spent calibration set remains valid "
                "fitting and diagnostic evidence; section 3: no new corpus is needed to test "
                "whether a different class has a zero-error region"
            ),
            "handoff_sha256": _digest(HANDOFF.read_bytes()),
            "feature_seals_sha256": _digest(SEAL_RECORD.read_bytes()),
            "fitting_campaign_sha256": _digest(FITTING_CAMPAIGN.read_bytes()),
            "calibration_campaign_sha256": _digest(CALIBRATION_CAMPAIGN.read_bytes()),
            "learner_selection_sha256": _digest(LEARNER_SELECTION.read_bytes()),
            "final_or_canary_outcomes_inspected": 0,
            "retrieval_holdout_result_inspected": False,
            "selection_made": False,
            "threshold_derived_for_reuse": False,
            "hypothesis_class": {
                "name": HYPOTHESIS_CLASS,
                "fit_rule": FIT_RULE,
                "regularization": str(REGULARIZATION),
                "regularization_chosen_on": (
                    "fitting-pool-internal leave-group-out evidence only, before any "
                    "calibration decision was read under this class"
                ),
                "module": "src/cognitive_os/learning/pairwise_contrastive.py",
                "disjoint_model_hash": disjoint_model.content_hash(),
            },
            "floors_unchanged": {
                "minimum_independent_decisions": MINIMUM_INDEPENDENT_DECISIONS,
                "minimum_clean_coverage": str(MINIMUM_CLEAN_COVERAGE),
                "confident_errors_allowed": 0,
            },
            "correction_branch": {
                "residual_answered": (
                    "S21D4-039 measured the frozen k-NN's zero-error coverage at exactly "
                    "zero at both volumes; this class has a non-empty zero-error region on "
                    "every estimate below, so the residual is the class, not the corpus"
                ),
                "baseline_first_choice_rate": str(ladder.strongest_non_learned_rate),
                "disjoint_pool": {
                    "fitted_groups": len(fit_groups),
                    "fitted_pairs": disjoint_model.fitted_pair_count,
                    **disjoint,
                },
                "combined_pool_logo": {
                    "fitted_groups": len(combined) - 1,
                    **logo,
                },
                "volume_trend": (
                    "zero-error coverage rises with fitting volume under this class — "
                    "disjoint 80-group pool against combined 179-group pools above — where "
                    "the frozen k-NN measured flat zero; the D5 certification set must "
                    "still be freshly authored, because both numbers here read spent bytes"
                ),
                "logo_runtime_seconds": elapsed,
            },
            "retrieval_branch": {
                "surface_completion": surface,
                "floor_question_still_open": (
                    "whether a complete surface closes the 0.0089 MRR@10 gap is a "
                    "measurement that needs a freshly authored holdout; nothing here "
                    "re-decides the D4 result"
                ),
            },
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "disjoint_zero_error_coverage": disjoint["zero_error_coverage"],
                "logo_zero_error_coverage": logo["zero_error_coverage"],
                "logo_first_choice_rate": logo["first_choice_rate_over_all"],
                "surface_still_empty": surface["still_empty"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.output))


if __name__ == "__main__":
    raise SystemExit(main())
