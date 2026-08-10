#!/usr/bin/env python3
"""S21D6-032 to S21D6-035. Load the sealed directions, measure the baseline, derive the bar, decide.

Four stages, four records, and the stage boundaries are the evidence rather than a convenience.
The shape is [`learner_selection_d5.py`](learner_selection_d5.py)'s, with one stage replaced and
one deleted, because D6 varies the admission rule and nothing else.

*`--stage directions` (S21D6-032)* is where D5 fitted. D6 does not: it resolves both sealed
directions out of D5's artifact store by the content hash D5 published, read-only, and refuses if
either does not rehash. `fitted_here: false` is the claim that separates this sprint from every
predecessor, and it is checkable rather than asserted -- a direction whose bytes moved would fail
here rather than quietly become a different experiment.

*`--stage baseline` (S21D6-033)* measures the deterministic ladder on the hundred certification
decisions, every rung recorded including the ineligible ones. No direction is loaded here; the
baseline is a property of the corpus.

*`--stage point` (S21D6-034)* derives the conformal bar. Once. The wrong margins come from the
conformal half -- D5's hundred spent calibration decisions, rebuilt from its released bytes and
never re-executed -- and the bar is the ceil((1-alpha)*(m+1))-th smallest of them at the
pre-registered alpha. This is the first stage in the whole sprint that reads a certification
margin.

*`--stage select` (S21D6-035)* is a second process. It reloads both directions and the sealed
derivations, re-scores, and re-derives passing the sealed point back, so `derive_conformal_point`
refuses if this run produced a different bar. That is the single-derivation rule enforced across a
restart. Then every cell is reported, the amended Section 2.3 decides eligibility, and Section 3.4
decides the ending.

Two gates, deliberately distinct, exactly as D5 kept them. *The margin floor decides abstention*
and runs at zero throughout: searching it on the certification set is the threshold search the
pre-registration forbids. *The conformal bar decides admission*, and it is derived rather than
chosen. What changed is only how the second one is computed.

One cell is selectable and both are reported. The 720 direction is the pre-registered candidate;
the 320 is re-scored and reported because Section 2.3 requires every cell and sweep point on the
record, and it may not be selected however it lands.

Nothing here encodes anything, fits anything, or writes to a predecessor's store.

    set -a && . ./.env.s21d6.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d6.py --stage directions
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d6.py --stage baseline
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d6.py --stage point
    UV_CACHE_DIR=.cache/uv uv run python scripts/learner_selection_d6.py --stage select
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
sys.path.insert(0, str(REPOSITORY / "scripts"))

# The store guard and the conformal-half rebuild live in `reality_campaign_d6` and are imported
# rather than copied. Both are exactly the kind of thing a second copy gets wrong: W1 found the
# forbidden-store list duplicated three times with one copy missing `s21d5`, and the conformal
# rebuild is only trustworthy because it self-verifies against D5's published matrix hash. One
# definition, one place to be wrong.
from reality_campaign_d6 import (  # noqa: E402
    _conformal_matrix,
    _isolated_pair,
)

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
from cognitive_os.learning.conformal_operating_point import (  # noqa: E402
    DERIVATION_READING,
    DERIVATION_RULE,
    ConformalOperatingPointV5,
    admitted_error_upper_bound,
    conformal_rank,
    derive_conformal_point,
)
from cognitive_os.learning.correction_catalogue_d5 import seal_d5_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d6 import seal_d6_corpus  # noqa: E402
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
)
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
)
from cognitive_os.learning.selective_operating_point import ScoredDecision  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d6-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d6-contracts.json"
AMENDMENT = EVIDENCE / "sprint-21d6-contracts-amendment-2.json"
SEAL_RECORD = EVIDENCE / "sprint-21d6-feature-seals.json"
CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d6-certification-campaign.json"
SNAPSHOTS = EVIDENCE / "sprint-21d6-snapshots.json"
INVARIANCE = EVIDENCE / "sprint-21d6-invariance-regression.json"
DIRECTIONS = EVIDENCE / "sprint-21d6-directions.json"
BASELINE = EVIDENCE / "sprint-21d6-baseline-ladder.json"
CONFORMAL_POINT = EVIDENCE / "sprint-21d6-conformal-point.json"
SELECTION = EVIDENCE / "sprint-21d6-learner-selection.json"

#: D5's released fit, and the store its two directions live in. Read-only on both counts.
D5_DIRECTION_FIT = EVIDENCE / "sprint-21d5-direction-fit.json"
D5_LEARNER_SELECTION = EVIDENCE / "sprint-21d5-learner-selection.json"
D5_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d5")

#: S21D6-012 froze it before any margin was read, and S21D6-013 forbade re-choosing it.
ALPHA = Decimal("0.20")

#: S21D6-015's ceiling on the Clopper-Pearson 95% upper bound among admitted decisions.
CEILING_C = Decimal("0.15")

#: One selectable cell, both reported. The order is the reporting order, smallest fit first.
VOLUME_POINTS: tuple[int, ...] = (320, 720)
SELECTABLE_ROWS = 720

#: The abstention gate at measurement time, held where D5 held it. Not a setting this wave may
#: move: a floor chosen against the certification decisions is a threshold fitted to the set the
#: selection is certified against.
MARGIN_FLOOR = Decimal("0")

DERIVED = "split_conformal"

#: The amended §2.3, verbatim as thresholds.
MINIMUM_INDEPENDENT_DECISIONS = 100
MINIMUM_CLEAN_COVERAGE = Decimal("0.40")
FINAL_GROUPS = 60
MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS = 20
INFERENCE_BUDGET_MS = Decimal("250")

#: §3.4's endings, by name, so a reader is never asked to infer which one fired.
STOP_ADMISSION_CONTRACT_REFUSED = "admission_contract_refused"
STOP_LEAK_BUDGET_EXCEEDED = "leak_budget_exceeded"
STOP_MARGIN_COVERAGE_BOUND = "margin_coverage_bound"
STOP_NO_QUANTILE = "no_quantile"

#: What D5's published aggregate says this sprint must reproduce when it re-scores the conformal
#: half. It is not a target: the halves, the direction and the envelope are all sealed, so a
#: different count means the reconstruction is wrong, not that the evidence moved. §3.2's whole
#: alpha argument is computed from the 720 entry.
D5_WRONG_ANSWERED = {320: 9, 720: 12}

#: What a stop leaves closed. Named exhaustively, because "nothing else was opened" is a claim
#: about absence and absence is what a list makes checkable.
DEPENDENT_NOT_OPENED = (
    "final A bodies, outcomes and manifest",
    "final B bodies, outcomes and manifest",
    "canary bodies, outcomes and manifest",
    "the promotion metamorphic submanifest's 120 nominal decisions",
    "the v3 artifact bound to a conformal point",
    "artifact promotion, activation, shadow and canary lifecycle",
    "Gate L2 conditions 10, 11, 13, 15, 16 and 18 through 27",
    "Sprint 22A domain expansion",
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The convention every D4, D5 and D6 record shares: hashed bytes are written bytes."""
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


def _services(engine: Any, artifact_root: Path) -> tuple[ArtifactService, RealityCampaignLedger]:
    artifacts = ArtifactService(
        ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
    )
    ledger = RealityCampaignLedger(PostgresEventStore(engine, build_default_event_catalog()))
    return artifacts, ledger


# ------------------------------------------------------------------------------ the two halves


async def _certification_matrix(
    artifacts: ArtifactService, ledger: RealityCampaignLedger
) -> FittedMatrix:
    """D6's four hundred rows, from the sealed vectors and the ledger's labels.

    Rebuilt rather than reloaded, for D5's reason: a selection that scored rows nobody scanned
    would be a selection about a different matrix, and the hash is what says these are the
    scanned ones.
    """
    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    row = next(
        item
        for item in sealed["partitions"]
        if item["partition"] == CorrectionPartition.CALIBRATION.value
    )
    data = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
    seal = SealedFeatureRecordSetV2.model_validate_json(data.decode())
    if seal.content_hash != row["feature_seal_hash"]:
        raise SystemExit("the stored certification seal is not the one S21D6-025 recorded")

    campaign = json.loads(CERTIFICATION_CAMPAIGN.read_text(encoding="utf-8"))
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
                partition=CorrectionPartition.CALIBRATION.value,
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
    matrix = FittedMatrix(split="calibration", rows=tuple(rows))
    expected = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    if matrix.content_hash != expected["certification_matrix_hash"]:
        raise SystemExit(
            f"the certification matrix is not the one S21D6-030 scanned: {matrix.content_hash} "
            f"against {expected['certification_matrix_hash']}"
        )
    return matrix


# ------------------------------------------------------------------------------- the decisions


@dataclass(frozen=True, slots=True)
class _Group:
    """One group as a ranking decision: one order, four vectors, four labels."""

    group: str
    order: tuple[str, ...]
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]
    #: Only the certification half has one. The conformal half places the bar and certifies
    #: nothing, so "changed against the baseline" is not a quantity it reports.
    baseline_first_choice: str | None
    #: The decision's identity for the census: the group's four fitted vectors, in slot order.
    signature: str


def _catalogue(half: str) -> Any:
    bundle = seal_d6_corpus() if half == "certification" else seal_d5_corpus()
    return bundle.catalogues[CorrectionPartition.CALIBRATION]


def _orders(catalogue: Any) -> dict[str, tuple[str, ...]]:
    return {
        group.repository_group: tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for group in catalogue.groups
    }


def _texts(catalogue: Any) -> tuple[dict[str, str], dict[str, str]]:
    """Requirement and per-candidate texts, for the lexical rung of the baseline ladder."""
    requirement: dict[str, str] = {}
    delta: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[recipe][module_path]
    return requirement, delta


def _ladder(matrix: FittedMatrix, catalogue: Any) -> tuple[Any, dict[str, tuple[str, ...]]]:
    """The deterministic ladder and the order its strongest rung would act on."""
    requirement, delta = _texts(catalogue)
    order = _orders(catalogue)
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


def _groups(
    matrix: FittedMatrix, catalogue: Any, baseline_order: dict[str, tuple[str, ...]] | None
) -> tuple[tuple[_Group, ...], DecisionCensusV4]:
    order = _orders(catalogue)
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
            baseline_first_choice=None if baseline_order is None else baseline_order[name][0],
            # A ranking decision's identity is the four fitted vectors it chooses among, in
            # slot order. Two groups sharing one would be one decision counted twice.
            signature=_digest("|".join(hashes[name][item] for item in order[name])),
        )
        for name in sorted(order)
    )
    return groups, DecisionCensusV4.from_feature_hashes([item.signature for item in groups])


def _score(
    model: PairwiseContrastiveModel, groups: tuple[_Group, ...]
) -> tuple[list[dict[str, Any]], Decimal]:
    """One direction over one half. Abstention only; admission is the bar's job."""
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
                "changed": (not ranking.abstained)
                and item.baseline_first_choice is not None
                and first != item.baseline_first_choice,
                "baseline_correct": (
                    None
                    if item.baseline_first_choice is None
                    else item.accepted[item.baseline_first_choice]
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


# ------------------------------------------------------------------------ the sealed directions


def _model_from_bytes(data: bytes) -> PairwiseContrastiveModel:
    payload = json.loads(data.decode())
    if payload.get("hypothesis_class") != HYPOTHESIS_CLASS:
        raise SystemExit(f"stored direction claims {payload.get('hypothesis_class')}")
    return PairwiseContrastiveModel(
        encoder_version=str(payload["encoder_version"]),
        feature_names=tuple(str(name) for name in payload["feature_names"]),
        weights=tuple(float(weight) for weight in payload["weights"]),
        regularization=str(payload["regularization"]),
        fitted_group_count=int(payload["fitted_group_count"]),
        fitted_pair_count=int(payload["fitted_pair_count"]),
    )


def _resolve_direction(item: dict[str, Any]) -> tuple[PairwiseContrastiveModel, Path, bytes]:
    """One of D5's sealed directions, out of D5's content-addressed store, read-only.

    Resolved by the content hash D5 published rather than re-fitted: a refit that happened to
    agree would be a coincidence rather than the same direction, and one that did not agree
    would silently be a different experiment with every field name still correct. The store is
    content-addressed, so the artifact id is a database key rather than a path -- and D6 does not
    open D5's database, which is why the lookup is a scan over the file names that *are* content
    addresses.
    """
    for path in sorted(D5_ARTIFACT_ROOT.rglob("*")):
        if not path.is_file() or len(path.name) != 64:
            continue
        data = path.read_bytes()
        if b'"hypothesis_class"' not in data:
            continue
        try:
            model = _model_from_bytes(data)
        except (KeyError, ValueError, SystemExit):
            continue
        if model.content_hash() == item["model_hash"]:
            if _digest(data) != path.name:
                raise SystemExit(f"{path.name} does not hash to its own content address")
            return model, path, data
    raise SystemExit(
        f"D5's sealed {item['volume_rows']}-row direction does not resolve in its artifact "
        "store; the direction D6 inherits cannot be read, and refitting it here would replace a "
        "predecessor's sealed bytes with this sprint's opinion of them"
    )


def _sealed_directions() -> dict[int, dict[str, Any]]:
    """Both directions, resolved and rehashed against D5's released record."""
    released = json.loads(D5_DIRECTION_FIT.read_text(encoding="utf-8"))
    loaded: dict[int, dict[str, Any]] = {}
    for item in released["models"]:
        model, path, data = _resolve_direction(item)
        loaded[int(item["volume_rows"])] = {
            "model": model,
            "path": path,
            "bytes": len(data),
            "released": item,
        }
    if sorted(loaded) != sorted(VOLUME_POINTS):
        raise SystemExit(f"D5 sealed {sorted(loaded)}, not {sorted(VOLUME_POINTS)}")
    return loaded


def _direction_record(volume: int, resolved: dict[str, Any]) -> dict[str, Any]:
    model: PairwiseContrastiveModel = resolved["model"]
    released = resolved["released"]
    magnitudes = sorted(abs(weight) for weight in model.weights)
    return {
        "volume_rows": volume,
        "volume_groups": volume // 4,
        "selectable": volume == SELECTABLE_ROWS,
        "fitted_group_count": model.fitted_group_count,
        "fitted_pair_count": model.fitted_pair_count,
        "model_hash": model.content_hash(),
        "d5_published_model_hash": released["model_hash"],
        "rehashes_to_the_published_direction": model.content_hash() == released["model_hash"],
        "d5_artifact_id": released["artifact_id"],
        "resolved_content_address": resolved["path"].name,
        "stored_bytes": resolved["bytes"],
        "d5_published_stored_bytes": released["stored_bytes"],
        "byte_length_matches": resolved["bytes"] == released["stored_bytes"],
        "regularization": model.regularization,
        "encoder_version": model.encoder_version,
        "weights": len(model.weights),
        "largest_absolute_weight": f"{magnitudes[-1]:.6g}",
        "median_absolute_weight": f"{magnitudes[len(magnitudes) // 2]:.6g}",
    }


# ------------------------------------------------------------------------------- S21D6-032


def _stage_directions(output: Path) -> int:
    """Resolve both sealed directions. Nothing is fitted and no margin is read."""
    directions = _sealed_directions()
    records = [_direction_record(volume, directions[volume]) for volume in VOLUME_POINTS]
    if not all(item["rehashes_to_the_published_direction"] for item in records):
        raise SystemExit("a resolved direction does not rehash to the one D5 published")

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-032"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "d5_direction_fit_sha256": _digest(D5_DIRECTION_FIT.read_bytes()),
            "final_outcomes_inspected": False,
            "hypothesis_class": HYPOTHESIS_CLASS,
            "fitted_here": False,
            "refitted": False,
            "fitting_rows_opened": 0,
            "certification_decisions_scored": 0,
            "conformal_margins_read": 0,
            "d5_store_opened_for_writing": False,
            "how_they_were_resolved": (
                "by the content hash D5 published, out of D5's content-addressed artifact store "
                "on disk, read-only. D6 does not open D5's database, so the artifact id is "
                "carried as provenance and the lookup runs over the file names that are content "
                "addresses; each resolved file is checked to hash to its own name as well"
            ),
            "why_no_fit_stage_exists": (
                "D5's typed stop licenses one successor experiment: a different confidence "
                "construction over the same ranker. Refitting the direction would confound the "
                "one thing this sprint varies, so the stage that fitted in D5 resolves in D6 "
                "and the record says `fitted_here: false` where D5's said `fit_rule`"
            ),
            "selectable_cell": SELECTABLE_ROWS,
            "reported_but_not_selectable": [
                volume for volume in VOLUME_POINTS if volume != SELECTABLE_ROWS
            ],
            "directions": records,
        }
    )
    _write(output, evidence)
    print(
        json.dumps(
            {
                "output": output.name,
                "directions": {
                    str(item["volume_rows"]): item["model_hash"][:16] for item in records
                },
                "rehashed": all(item["rehashes_to_the_published_direction"] for item in records),
                "fitted_here": False,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D6-033


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
    database_url, artifact_root = _isolated_pair()
    engine = create_postgres_engine(database_url)
    try:
        artifacts, ledger = _services(engine, artifact_root)
        certification = await _certification_matrix(artifacts, ledger)
    finally:
        await engine.dispose()

    catalogue = _catalogue("certification")
    ladder, baseline_order = _ladder(certification, catalogue)
    groups, census = _groups(certification, catalogue, baseline_order)
    rungs = _rungs(ladder)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-033"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "certification_campaign_sha256": _digest(CERTIFICATION_CAMPAIGN.read_bytes()),
            "final_outcomes_inspected": False,
            "certification_matrix_hash": certification.content_hash,
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
                "measured_on": "the same certification decisions the direction is measured on",
                "no_direction_loaded": True,
                "rungs": rungs,
            },
            "why_every_rung_including_the_ineligible_ones": (
                "the selection rule compares the learner against the strongest deterministic "
                "baseline, and 'strongest' is only meaningful if the weaker rungs are on the "
                "record too. An ineligible rung is recorded with the reason it is ineligible, "
                "so a reader can see that the comparison was not narrowed to a rung the "
                "learner happens to beat"
            ),
            "why_the_baseline_is_measured_on_the_certification_half": (
                "the conformal half places the bar and certifies nothing, so a baseline over it "
                "would compare the learner against a rung on decisions nobody is certifying"
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


# ------------------------------------------------------------------------------- S21D6-034


@dataclass(frozen=True, slots=True)
class _Halves:
    """Everything both stages need, assembled once so the two cannot disagree about it."""

    conformal: FittedMatrix
    conformal_report: dict[str, Any]
    certification: FittedMatrix
    conformal_groups: tuple[_Group, ...]
    certification_groups: tuple[_Group, ...]
    conformal_census: DecisionCensusV4
    certification_census: DecisionCensusV4
    ladder: Any
    directions: dict[int, dict[str, Any]]
    source_hash: str


async def _halves() -> _Halves:
    database_url, artifact_root = _isolated_pair()
    engine = create_postgres_engine(database_url)
    try:
        artifacts, ledger = _services(engine, artifact_root)
        certification = await _certification_matrix(artifacts, ledger)
    finally:
        await engine.dispose()

    conformal, conformal_report = _conformal_matrix()
    published = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))["fitted_matrices"]
    if conformal.content_hash != published["conformal_matrix_hash"]:
        raise SystemExit(
            f"the conformal matrix is not the one S21D6-030 scanned: {conformal.content_hash} "
            f"against {published['conformal_matrix_hash']}"
        )

    certification_catalogue = _catalogue("certification")
    ladder, baseline_order = _ladder(certification, certification_catalogue)
    certification_groups, certification_census = _groups(
        certification, certification_catalogue, baseline_order
    )
    conformal_groups, conformal_census = _groups(conformal, _catalogue("conformal"), None)
    return _Halves(
        conformal=conformal,
        conformal_report=conformal_report,
        certification=certification,
        conformal_groups=conformal_groups,
        certification_groups=certification_groups,
        conformal_census=conformal_census,
        certification_census=certification_census,
        ladder=ladder,
        directions=_sealed_directions(),
        # Both halves, by identity. The bar's *value* is a function of the conformal half alone,
        # but the record this hash seals is a statement about a measurement over the pair, so a
        # swapped certification half must change the derivation hash even if its aggregates
        # happened to coincide.
        source_hash=_digest(
            f"conformal={conformal.content_hash}\ncertification={certification.content_hash}"
        ),
    )


def _wrong_margins(decisions: list[dict[str, Any]]) -> list[Decimal]:
    return sorted(
        Decimal(str(item["score"]))
        for item in decisions
        if item["answered"] and not item["correct"]
    )


def _conformal_half_report(volume: int, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """What the bar was read off, and the check that says the reconstruction is D5's."""
    margins = _wrong_margins(decisions)
    answered = [item for item in decisions if item["answered"]]
    expected = D5_WRONG_ANSWERED[volume]
    if len(margins) != expected:
        raise SystemExit(
            f"the rebuilt conformal half yields {len(margins)} wrong answered decisions at "
            f"{volume} rows, where D5 published {expected}. The halves, the direction and the "
            "clip-and-scale envelope are all sealed, so this is a broken reconstruction rather "
            "than moved evidence, and a bar read off it would not be the pre-registered one"
        )
    return {
        "answered_decisions": len(answered),
        "wrong_answered_decisions": len(margins),
        "d5_published_wrong_answered": expected,
        "reproduces_d5_s_published_count": True,
        "wrong_margins": [str(item) for item in margins],
        "quantile_rank": conformal_rank(ALPHA, len(margins)),
        "wrong_margins_left_above_the_bar": max(
            0, len(margins) - conformal_rank(ALPHA, len(margins))
        ),
        "what_this_check_is_for": (
            "§3.2 computed the alpha floor from D5's published wrong-decision count. If the "
            "rebuilt half yielded another count, the alpha argument would have been made about "
            "a different distribution than the one the bar is read off"
        ),
    }


def _point_record(point: ConformalOperatingPointV5) -> dict[str, Any]:
    return {
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
        "split": point.split,
        "calibration_source_hash": point.calibration_source_hash,
        "preregistration_hash": point.preregistration_hash,
        "conformal_census": point.conformal_census.model_dump(
            mode="json", exclude={"content_hash"}
        ),
        "certification_census": point.certification_census.model_dump(
            mode="json", exclude={"content_hash"}
        ),
        "derived_at": point.derived_at.isoformat(),
        "canonical": point.model_dump(mode="json"),
    }


async def _stage_point(output: Path) -> int:
    """Derive the conformal bar once per direction, from the conformal half only."""
    halves = await _halves()
    preregistration_hash = _digest(PRE_REGISTRATION.read_bytes())
    derivations: list[dict[str, Any]] = []
    for volume in VOLUME_POINTS:
        model = halves.directions[volume]["model"]
        conformal, _ = _score(model, halves.conformal_groups)
        certification, slowest = _score(model, halves.certification_groups)
        point = derive_conformal_point(
            _scored(conformal),
            _scored(certification),
            alpha=ALPHA,
            split="calibration",
            calibration_source_hash=halves.source_hash,
            preregistration_hash=preregistration_hash,
            derived_at=utc_now(),
        )
        derivations.append(
            {
                "volume_rows": volume,
                "selectable": volume == SELECTABLE_ROWS,
                "model_hash": model.content_hash(),
                "conformal_half": _conformal_half_report(volume, conformal),
                "certification_answered_decisions": sum(
                    1 for item in certification if item["answered"]
                ),
                "maximum_inference_ms_per_candidate": str(slowest),
                "point": _point_record(point),
            }
        )

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-034"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": preregistration_hash,
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "amendment_2_sha256": _digest(AMENDMENT.read_bytes()),
            "directions_sha256": _digest(DIRECTIONS.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "certification_campaign_sha256": _digest(CERTIFICATION_CAMPAIGN.read_bytes()),
            "final_outcomes_inspected": False,
            "derivation_rule": DERIVATION_RULE,
            "derivation_reading": DERIVATION_READING,
            "alpha": str(ALPHA),
            "alpha_rechosen": False,
            "split": "calibration",
            "margin_floor_at_measurement": str(MARGIN_FLOOR),
            "halves": {
                "conformal": halves.conformal_report,
                "certification": {
                    "role": "d6's own, freshly authored and executed in W1",
                    "rows": len(halves.certification.rows),
                    "groups": len(halves.certification.groups),
                    "matrix_hash": halves.certification.content_hash,
                    "independent_decisions": halves.certification_census.independent_decisions,
                },
                "calibration_source_hash": halves.source_hash,
                "what_the_source_hash_binds": (
                    "both halves by identity: sha256 over the conformal and certification matrix "
                    "hashes. The bar's value is a function of the conformal half alone, but the "
                    "derivation this hash seals is a measurement over the pair"
                ),
                "share_no_fitted_vector": True,
                "share_no_group": True,
            },
            "derivations": derivations,
            "single_derivation": {
                "derived_here": len(derivations),
                "one_per_direction": True,
                "why_two_derivations_are_not_two_bars": (
                    "the rule is one bar per (direction, calibration source) pair. Two "
                    "directions are two rankers, so each derives its own bar once; neither is a "
                    "second attempt at the other's, and only the 720 one is selectable"
                ),
                "enforced_across_restart_by": (
                    "S21D6-035, a separate process, which reloads these derivations and passes "
                    "each back to derive_conformal_point as `previous`; a different bar raises "
                    "ConformalPointError there rather than being written here"
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
                        "wrong_in_conformal_half": item["conformal_half"][
                            "wrong_answered_decisions"
                        ],
                        "rank": item["point"]["quantile_rank"],
                        "threshold": item["point"]["threshold"],
                        "admitted": item["point"]["admitted_decisions"],
                        "errors": item["point"]["errors_admitted"],
                        "coverage": item["point"]["coverage"],
                        "cp95": item["point"]["error_upper_bound_95"],
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


# ------------------------------------------------------------------------------- S21D6-035


def _cell(
    *,
    volume: int,
    threshold: Decimal | None,
    decisions: list[dict[str, Any]],
    slowest: Decimal,
    independent: int,
    baseline_rate: Decimal,
    derivation: dict[str, Any],
) -> dict[str, Any]:
    """One (direction, conformal bar) cell, with every denominator named."""
    answered = [item for item in decisions if item["answered"]]
    admitted = [
        item
        for item in answered
        if threshold is not None and Decimal(str(item["score"])) > threshold
    ]
    errors = [item for item in admitted if not item["correct"]]
    changed = [item for item in admitted if item["changed"]]
    # The leak: the share of *this half's* wrong answered decisions that cleared the bar. It is
    # the quantity alpha bounds, and it is the only way to tell a rule that worked on a harder
    # corpus from two halves that were not exchangeable. Reported rather than gating -- the
    # amended §2.3 reads the Clopper-Pearson bound, not this -- but never left unmeasured, or
    # the record would be asserting a guarantee it never looked at.
    wrong_answered = [item for item in answered if not item["correct"]]
    leak_rate = Decimal(len(errors)) / Decimal(len(wrong_answered)) if wrong_answered else None
    coverage = Decimal(len(admitted)) / Decimal(independent)
    first_choice_rate = (
        Decimal(len(admitted) - len(errors)) / Decimal(len(admitted)) if admitted else None
    )
    projected = (
        (Decimal(len(changed)) / Decimal(len(admitted)) * FINAL_GROUPS) if admitted else Decimal(0)
    )
    bound = (
        Decimal(str(round(admitted_error_upper_bound(len(errors), len(admitted)), 6)))
        if admitted
        else None
    )
    return {
        "operating_point": DERIVED,
        "alpha": str(ALPHA),
        "threshold": None if threshold is None else str(threshold),
        "volume_rows": volume,
        "selectable": volume == SELECTABLE_ROWS,
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
            "why_it_can_exceed_alpha_on_one_sample": (
                "the conformal guarantee is marginal and holds in expectation over exchangeable "
                "halves, so one realised sample may exceed the budget. A realised leak far above "
                "alpha alongside a coverage far from the design's expectation is the symptom "
                "§6 named for the exchangeability the evidence cannot retire"
            ),
        },
        "changed_decisions": len(changed),
        "projected_changed_final_decisions": str(round(projected, 3)),
        "maximum_inference_ms": str(slowest),
        "within_inference_budget": slowest <= INFERENCE_BUDGET_MS,
        "fully_abstaining": not answered,
        "filtered_no_changed_decision": not changed,
        "conformal_bar_derivation": derivation,
    }


def _satisfies_section_2_3(
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


def _sweep(
    decisions: list[dict[str, Any]], *, independent: int, baseline_rate: Decimal
) -> list[dict[str, Any]]:
    """The whole risk-coverage curve: every distinct margin, reported, none of them selectable.

    Not a grid: no point here may be chosen, because choosing a threshold on the certification
    set is the search §3.5 forbids. Only the derived conformal bar is a cell.
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
                "errors_admitted": len(errors),
                "coverage": str(Decimal(len(admitted)) / Decimal(independent)),
                "first_choice_rate_over_admitted": str(
                    Decimal(len(admitted) - len(errors)) / Decimal(len(admitted))
                ),
                "error_upper_bound_95": str(
                    round(admitted_error_upper_bound(len(errors), len(admitted)), 6)
                ),
                "baseline_first_choice_rate": str(baseline_rate),
                "changed_decisions": len(changed),
                "selectable": False,
            }
        )
    return points


def _joint_feasibility(sweep: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether the amended §2.3 pair is reachable *anywhere* on this cell's curve.

    §2.1 priced the pre-amendment pair and found it infeasible rather than merely unmet, and
    that distinction is the whole argument for amendment 2. The same question has to be asked of
    the amended pair, or the record reports a bar that missed without saying whether any bar
    could have cleared it -- and a successor sprint would then be sized against the wrong
    constraint.

    This searches nothing. Every point here is already reported and none of them is selectable;
    what is computed is the *absence* of a satisfying point, which is a property of the curve
    rather than a threshold anybody could adopt.
    """
    satisfying = [
        point
        for point in sweep
        if Decimal(point["coverage"]) >= MINIMUM_CLEAN_COVERAGE
        and Decimal(point["error_upper_bound_95"]) <= CEILING_C
    ]
    under_the_ceiling = [
        Decimal(point["coverage"])
        for point in sweep
        if Decimal(point["error_upper_bound_95"]) <= CEILING_C
    ]
    at_the_floor = [
        Decimal(point["error_upper_bound_95"])
        for point in sweep
        if Decimal(point["coverage"]) >= MINIMUM_CLEAN_COVERAGE
    ]
    return {
        "sweep_points": len(sweep),
        "points_satisfying_both": len(satisfying),
        "pair_is_reachable_at_any_threshold": bool(satisfying),
        "best_coverage_under_the_ceiling": str(max(under_the_ceiling))
        if under_the_ceiling
        else "0",
        "best_bound_at_or_above_the_coverage_floor": (
            str(min(at_the_floor)) if at_the_floor else None
        ),
        "coverage_floor": str(MINIMUM_CLEAN_COVERAGE),
        "ceiling_c": str(CEILING_C),
        "reading": (
            "no threshold on this curve satisfies the amended §2.3 pair, so the bar's placement "
            "is not what the cell failed on. A different alpha moves the bar along this same "
            "curve and every point on it misses"
            if not satisfying
            else f"{len(satisfying)} reported points satisfy the pair; the derived bar is not "
            "among them, and none of them is selectable -- choosing one would be the threshold "
            "search the pre-registration forbids"
        ),
        "not_selectable": (
            "reported because §2.3 requires every point on the record. A point that satisfies "
            "the pair is not a candidate: the bar is derived once from the conformal half, and a "
            "threshold picked off the certification curve is fitted to the set it certifies"
        ),
    }


def _classify(cell: dict[str, Any], *, eligible: bool) -> tuple[str | None, str]:
    """§3.4's tree, evaluated on the selectable cell only. The record must not guess."""
    if eligible:
        return None, (
            "step 1: every amended §2.3 condition holds on the pre-registered 720 cell -- at "
            "least 100 independent decisions, admission by the split-conformal bar at alpha with "
            "a Clopper-Pearson 95% upper bound at or below 0.15, coverage at least 0.40, at "
            "least 20 projected changed final decisions, a first-choice rate above the strongest "
            "deterministic baseline, at least one changed decision, first-action preservation, "
            "every point reported and inference inside the budget. Selection proceeds"
        )
    if not cell["conformal_bar_derivation"]["quantile_exists"]:
        return STOP_NO_QUANTILE, (
            "step 4: no quantile exists. §3.4 calls this unreachable by construction -- the rank "
            f"at alpha {ALPHA} is {cell['conformal_bar_derivation']['quantile_rank']} and the "
            "conformal half was sealed with 12 wrong decisions -- so this outcome says the "
            "derivation is wrong rather than that the evidence is"
        )
    coverage = Decimal(str(cell["coverage"]))
    if coverage < MINIMUM_CLEAN_COVERAGE:
        return STOP_MARGIN_COVERAGE_BOUND, (
            f"step 3: clean coverage is {coverage} at the pre-registered alpha, below the 0.40 "
            "floor. The margin does not concentrate the ranker's errors at low margins on "
            "evidence nobody had read. The confidence construction has now been varied twice and "
            "failed twice, and the next axis is the hypothesis class rather than a third bar"
        )
    if not cell["within_the_ceiling"]:
        leak = cell["leak"]
        held = (
            f"the bar held its leak guarantee -- {leak['wrong_answered_decisions_admitted']} of "
            f"{leak['wrong_answered_decisions']} wrong decisions cleared it, a realised leak of "
            f"{leak['realised_leak_rate']} against the {ALPHA} budget -- and the admitted "
            "precision still missed"
        )
        missed = (
            f"The realised leak is {leak['realised_leak_rate']}, itself above the {ALPHA} "
            f"budget: {leak['wrong_answered_decisions_admitted']} of "
            f"{leak['wrong_answered_decisions']} wrong decisions cleared the bar. §3.4's step 2 "
            "is worded for a bar that held its guarantee and missed the ceiling anyway; this "
            "one missed both, which is the shape §6 named as the exchangeability symptom rather "
            "than a defect in the rule. It is recorded here rather than smoothed into the "
            "typed ending"
        )
        feasibility = cell["joint_feasibility"]
        volume = (
            ". A tighter alpha needs more than 12 wrong decisions in the conformal half, which "
            "is a corpus-volume question and the first measured reason this programme would have "
            "to author more"
        )
        # The sealed step-2 sentence points the successor at conformal-half volume, on the
        # premise that a tighter alpha would have cleared the ceiling. The sweep can say whether
        # that premise holds on this evidence, and where it does not, the record says so rather
        # than handing a successor sprint a target the curve rules out.
        unreachable = (
            f". And no threshold on this cell's {feasibility['sweep_points']}-point curve "
            f"satisfies the amended pair at all: the best Clopper-Pearson bound anywhere at or "
            f"above the 0.40 coverage floor is "
            f"{feasibility['best_bound_at_or_above_the_coverage_floor']}, and no point of any "
            f"coverage reaches the {CEILING_C} ceiling. A tighter alpha moves the bar along this "
            "same curve, so §3.4's step-2 sentence -- more wrong decisions in the conformal half "
            "-- is not what this cell failed on. What binds is the ranker's error rate on this "
            "corpus, which is a hypothesis-class question rather than a volume one. Recorded "
            "here because §2.1 drew exactly this distinction for the pre-amendment pair, and "
            "'infeasible' and 'unmet' size two different successors"
        )
        return STOP_LEAK_BUDGET_EXCEEDED, (
            f"step 2: coverage is {coverage}, at or above the floor, and the Clopper-Pearson 95% "
            f"upper bound on the error rate among admitted decisions is "
            f"{cell['error_upper_bound_95']}, above the pre-registered ceiling {CEILING_C}. "
            + (held if leak["within_the_leak_budget"] else missed)
            + (volume if feasibility["pair_is_reachable_at_any_threshold"] else unreachable)
        )
    return STOP_LEAK_BUDGET_EXCEEDED, (
        "coverage and the bound both hold and a different §2.3 condition failed; the failing "
        f"conditions are named in `ineligible_reasons` on the cell: {cell['ineligible_reasons']}. "
        "§3.4 types no ending for this shape, so the nearest one is recorded together with the "
        "reason it is not a clean fit, rather than inventing a fifth ending after the measurement"
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
            "alpha": selected["alpha"],
            "threshold": selected["threshold"],
            "volume_rows": selected["volume_rows"],
            "coverage": selected["coverage"],
            "first_choice_rate_over_admitted": selected["first_choice_rate_over_admitted"],
            "errors_admitted": selected["errors_admitted"],
            "error_upper_bound_95": selected["error_upper_bound_95"],
            "changed_decisions": selected["changed_decisions"],
            "projected_changed_final_decisions": selected["projected_changed_final_decisions"],
            "maximum_inference_ms": selected["maximum_inference_ms"],
        }
    return {
        "outcome": "null",
        "immutable": True,
        "stop_kind": stop,
        "reading": reading,
        "dependent_not_opened": list(DEPENDENT_NOT_OPENED),
        "why_a_null_and_not_a_weaker_candidate": (
            "the amended §2.3's conditions are the selection rule, not a preference. A cell that "
            "fails one is not a worse candidate, it is not a candidate"
        ),
    }


async def _stage_select(output: Path) -> int:
    halves = await _halves()
    preregistration_hash = _digest(PRE_REGISTRATION.read_bytes())
    independent = halves.certification_census.independent_decisions
    baseline_rate = Decimal(
        sum(
            1
            for item in halves.certification_groups
            if item.baseline_first_choice is not None and item.accepted[item.baseline_first_choice]
        )
    ) / Decimal(independent)

    invariance = json.loads(INVARIANCE.read_text(encoding="utf-8"))
    first_action_preserved = (
        int(invariance["first_action"]["changes"]) == 0
        and int(invariance["independence"]["vectors_changed"]) == 0
        and not invariance["stops"]
    )
    sealed_points = {
        int(item["volume_rows"]): item
        for item in json.loads(CONFORMAL_POINT.read_text(encoding="utf-8"))["derivations"]
    }

    cells: list[dict[str, Any]] = []
    curve: dict[str, Any] = {}
    reproduced = 0
    for volume in VOLUME_POINTS:
        model = halves.directions[volume]["model"]
        conformal, _ = _score(model, halves.conformal_groups)
        certification, slowest = _score(model, halves.certification_groups)
        previous = ConformalOperatingPointV5.model_validate(
            sealed_points[volume]["point"]["canonical"]
        )
        # The single-derivation rule across a restart: a different bar raises here.
        point = derive_conformal_point(
            _scored(conformal),
            _scored(certification),
            alpha=ALPHA,
            split="calibration",
            calibration_source_hash=halves.source_hash,
            preregistration_hash=preregistration_hash,
            derived_at=utc_now(),
            previous=previous,
        )
        reproduced += 1
        derivation = _point_record(point)
        derivation.pop("canonical")
        derivation["conformal_half"] = _conformal_half_report(volume, conformal)
        threshold = None if point.threshold is None else Decimal(point.threshold)
        sweep = _sweep(certification, independent=independent, baseline_rate=baseline_rate)
        cell = _cell(
            volume=volume,
            threshold=threshold,
            decisions=certification,
            slowest=slowest,
            independent=independent,
            baseline_rate=baseline_rate,
            derivation=derivation,
        )
        cell["model_hash"] = model.content_hash()
        cell["joint_feasibility"] = _joint_feasibility(sweep)
        cell["ineligible_reasons"] = _satisfies_section_2_3(
            cell, first_action_preserved=first_action_preserved, sweep_points=len(sweep)
        )
        cells.append(cell)

        answered = [item for item in certification if item["answered"]]
        rates = [Decimal(str(item["first_choice_rate_over_admitted"])) for item in sweep]
        curve[str(volume)] = {
            "exemplar_rows": volume,
            "exemplar_groups": volume // 4,
            "selectable": volume == SELECTABLE_ROWS,
            "model_hash": model.content_hash(),
            "fitted_pair_count": halves.directions[volume]["released"]["fitted_pair_count"],
            "conformal_coverage": cell["coverage"],
            "conformal_threshold": cell["threshold"],
            "answered_decisions": len(answered),
            "first_choice_rate_over_all_answered": str(
                Decimal(sum(1 for item in answered if item["correct"])) / Decimal(len(answered))
            )
            if answered
            else None,
            "baseline_first_choice_rate": str(baseline_rate),
            "changed_decisions_over_all_answered": sum(1 for item in answered if item["changed"]),
            "errors_admitted_at_the_derived_bar": cell["errors_admitted"],
            "errors_among_all_answered": sum(1 for item in answered if not item["correct"]),
            "sweep_points": len(sweep),
            "best_first_choice_rate_over_admitted": str(max(rates)) if rates else None,
            "deepest_error_free_prefix_by_margin": max(
                (
                    int(item["admitted_decisions"])
                    for item in sweep
                    if int(item["errors_admitted"]) == 0
                ),
                default=0,
            ),
            "what_the_zero_error_prefix_rule_would_have_admitted": max(
                (
                    int(item["admitted_decisions"])
                    for item in sweep
                    if int(item["errors_admitted"]) == 0
                ),
                default=0,
            ),
            "sweep": sweep,
        }

    selectable = next(cell for cell in cells if cell["selectable"])
    eligible = not selectable["ineligible_reasons"]
    stop, reading = _classify(selectable, eligible=eligible)
    selected = selectable if eligible else None

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-035"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": preregistration_hash,
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "amendment_2_sha256": _digest(AMENDMENT.read_bytes()),
            "snapshots_sha256": _digest(SNAPSHOTS.read_bytes()),
            "invariance_regression_sha256": _digest(INVARIANCE.read_bytes()),
            "directions_sha256": _digest(DIRECTIONS.read_bytes()),
            "baseline_ladder_sha256": _digest(BASELINE.read_bytes()),
            "conformal_point_sha256": _digest(CONFORMAL_POINT.read_bytes()),
            "certification_campaign_sha256": _digest(CERTIFICATION_CAMPAIGN.read_bytes()),
            "d5_learner_selection_sha256": _digest(D5_LEARNER_SELECTION.read_bytes()),
            "final_or_canary_outcomes_inspected": 0,
            "final_outcomes_inspected": False,
            "hypothesis_class": HYPOTHESIS_CLASS,
            "fitted_here": False,
            "decisions": {
                "census": halves.certification_census.model_dump(
                    mode="json", exclude={"content_hash", "independence_rule"}
                ),
                "independent_decisions": independent,
                "identity_rule": (
                    "a ranking decision is identified by its four fitted feature vectors in "
                    "slot order; two groups sharing one would be one decision counted twice"
                ),
                "certification_matrix_hash": halves.certification.content_hash,
                "conformal_matrix_hash": halves.conformal.content_hash,
                "matrices_are_the_scanned_ones": True,
                "conformal_independent_decisions": (halves.conformal_census.independent_decisions),
            },
            "baseline": {
                "strongest_deterministic_rung": halves.ladder.strongest_non_learned_name,
                "ladder_hash": halves.ladder.content_hash,
                "first_choice_rate": str(baseline_rate),
                "measured_on": "the same 100 certification decisions the direction is measured on",
                "record": BASELINE.name,
                "rungs": _rungs(halves.ladder),
            },
            "two_gates": {
                "abstention": (
                    f"the margin floor, held at {MARGIN_FLOOR} throughout. It is not searched: a "
                    "floor chosen against these decisions would be a threshold fitted to the "
                    "certification set"
                ),
                "admission": (
                    f"the split-conformal bar at alpha {ALPHA}, one per direction, derived in "
                    "S21D6-034 from the conformal half and reproduced here across a process "
                    "restart"
                ),
                "what_changed_from_d5": (
                    "only the second one. D5 walked the margin ordering to its first wrong "
                    "decision; D6 takes the ceil((1-alpha)*(m+1))-th smallest wrong margin. Same "
                    "ranker, same encoder, same floor, same corpus contract"
                ),
            },
            "single_derivation_across_restart": {
                "derivations_reproduced": reproduced,
                "how": (
                    "each sealed ConformalOperatingPointV5 from S21D6-034 is passed back to "
                    "derive_conformal_point as `previous` in this separate process; a different "
                    "derivation hash raises ConformalPointError instead of writing a second bar"
                ),
                "sealed_derivation_hashes": {
                    str(volume): sealed_points[volume]["point"]["derivation_hash"]
                    for volume in VOLUME_POINTS
                },
            },
            "grid": {
                "cells_reported": len(cells),
                "selectable_cells": sum(1 for cell in cells if cell["selectable"]),
                "operating_points": [DERIVED],
                "volume_points": list(VOLUME_POINTS),
                "fully_abstaining_cells": sum(1 for cell in cells if cell["fully_abstaining"]),
                "filtered_no_changed_decision": sum(
                    1 for cell in cells if cell["filtered_no_changed_decision"]
                ),
                "sweep_points_reported": sum(
                    int(curve[str(volume)]["sweep_points"]) for volume in VOLUME_POINTS
                ),
                "why_one_cell_is_selectable_and_two_are_reported": (
                    "revision 6 pre-registers one class, one lambda, one direction and one "
                    "alpha, so there is nothing to search over -- which is the property that "
                    "makes a single derivation meaningful. The 320 direction is re-scored and "
                    "reported because §2.3 requires every cell and sweep point on the record, "
                    "and it may not be selected however it lands"
                ),
            },
            "risk_coverage_curve": curve,
            "section_2_3_as_amended": {
                "amendment": "sprint-21d6-contracts-amendment-2.json",
                "minimum_independent_decisions": MINIMUM_INDEPENDENT_DECISIONS,
                "alpha": str(ALPHA),
                "ceiling_c": str(CEILING_C),
                "minimum_clean_coverage": str(MINIMUM_CLEAN_COVERAGE),
                "minimum_projected_changed_final_decisions": (
                    MINIMUM_PROJECTED_CHANGED_FINAL_DECISIONS
                ),
                "final_groups": FINAL_GROUPS,
                "inference_budget_ms": str(INFERENCE_BUDGET_MS),
                "first_action_preservation_on_the_invariance_sample": first_action_preserved,
                "evaluated_on": "the selectable 720 cell only",
                "eligible": eligible,
                "ineligibility_counts": _reasons(cells),
                "thresholds_changed": 0,
                "what_the_ceiling_replaces": (
                    "'exactly zero confident errors', which at D5's 27 admitted decisions "
                    "bounded the same quantity at 0.105 by the same Clopper-Pearson construction"
                ),
            },
            "selection": _selection_block(selected, stop, reading),
            "decision_tree": {
                "section": "3.4",
                "reading": reading,
                "stop": stop,
                "amendment_refused": False,
                "why_step_0_did_not_fire": (
                    "the gate owner granted amendment 2 in W0, before any D6 measurement "
                    "existed; the record carries `measured_values: 0` and the chronology proving "
                    "it"
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
                "baseline": halves.ladder.strongest_non_learned_name,
                "baseline_first_choice_rate": str(baseline_rate),
                "conformal_coverage": {
                    key: value["conformal_coverage"] for key, value in curve.items()
                },
                "errors_admitted": {
                    str(cell["volume_rows"]): cell["errors_admitted"] for cell in cells
                },
                "realised_leak_rate": {
                    str(cell["volume_rows"]): cell["leak"]["realised_leak_rate"] for cell in cells
                },
                "amended_pair_reachable_at_any_threshold": {
                    str(cell["volume_rows"]): cell["joint_feasibility"][
                        "pair_is_reachable_at_any_threshold"
                    ]
                    for cell in cells
                },
                "error_upper_bound_95": {
                    str(cell["volume_rows"]): cell["error_upper_bound_95"] for cell in cells
                },
                "first_choice_rate_over_all_answered": {
                    key: value["first_choice_rate_over_all_answered"]
                    for key, value in curve.items()
                },
                "cells": len(cells),
                "eligible": eligible,
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


_STAGES: dict[str, tuple[Any, Path]] = {
    "directions": (_stage_directions, DIRECTIONS),
    "baseline": (_stage_baseline, BASELINE),
    "point": (_stage_point, CONFORMAL_POINT),
    "select": (_stage_select, SELECTION),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=sorted(_STAGES), required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    stage, default = _STAGES[arguments.stage]
    output = arguments.output or default
    if arguments.stage == "directions":
        return int(stage(output))
    if not os.environ.get("COGOS_DATABASE_URL"):
        raise SystemExit("COGOS_DATABASE_URL is required; source .env.s21d6.measured.local first")
    return int(asyncio.run(stage(output)))


if __name__ == "__main__":
    raise SystemExit(main())
