#!/usr/bin/env python3
"""S21D7-039: what the promoted artifact does on evidence it has never seen.

Conditions 13, 14, 15, 16 and 21, measured once over the two final batches. They belong in one
command because they are five readings of one comparison — the artifact's ordering against the
strongest deterministic rung on the same 60 groups — and splitting them would let each pick its
own denominator.

*The artifact does the ranking, not a re-fit.* The bytes are read out of D7's store, rehashed
and rebuilt through the evaluation boundary, so the numbers below are the promoted component's
and not a model that happens to hash the same. A gain measured with a re-fitted direction would
be a claim about the fitting code.

*The baseline is measured on the final batches, not carried over.* Which released rung is
strongest is a property of a corpus, and the final groups are D2's, not the certification half's.
The ladder is run on each batch and the strongest is derived rather than named.

*The bootstrap is paired and resamples groups, not decisions.* The two orderings answer the same
60 groups, so the quantity with a distribution is the per-group difference; resampling decisions
independently would break the pairing that makes the comparison sharp. Ten thousand resamples
under a fixed seed, so the interval reproduces.

*Shadow is a claim about what executed, not about what was computed.* The learned ordering is
computed for every final group and compared with what the runtime actually acted on; with the
ledger row in SHADOW the resolver refuses the learned path, so the executed ordering must be the
deterministic one on all 60 groups and the learned ordering must reach no outcome.

    set -a && . ./.env.s21d7.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/final_evidence_d7.py

Reads the final outcomes: this is the record that opens them, and it says so. No store is
written, no bar is derived and no threshold moves.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.learned_runtime import (  # noqa: E402
    ActiveComponentState,
    ArtifactAvailability,
    EmbeddingIdentity,
    LearnedRuntimeResolver,
    RoutingPolicy,
    RuntimeHealthReason,
)
from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.learned import LearnedComponentState  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.learning.containment_contrastive import (  # noqa: E402
    ContainmentContrastiveRanker,
    relational_numbers,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_ranker_for_evaluation_v3,
)
from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    SealedFeatureRecordSetV2,
)
from cognitive_os.learning.correction_ladder import build_ladder, eligible_rungs  # noqa: E402
from cognitive_os.learning.correction_ladder import (  # noqa: E402
    group_candidates as ladder_groups,
)
from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow  # noqa: E402
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-final-evidence.json"

ARTIFACT = EVIDENCE / "sprint-21d7-artifact.json"
FINAL_SEALS = EVIDENCE / "sprint-21d7-final-feature-seals.json"
FINAL_CAMPAIGN = {
    CorrectionPartition.FINAL_A: EVIDENCE / "sprint-21d7-final-a-campaign.json",
    CorrectionPartition.FINAL_B: EVIDENCE / "sprint-21d7-final-b-campaign.json",
}
FINAL_ROLE_AUDIT = EVIDENCE / "sprint-21d7-final-role-audit.json"
SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

#: Fixed forever, so the interval reproduces. A bootstrap whose seed moves is a bootstrap whose
#: interval can be shopped for.
BOOTSTRAP_SEED = 21_070_039
BOOTSTRAP_RESAMPLES = 10_000

#: §2.4's floors for the four conditions this record decides.
MINIMUM_CHANGED_FINAL_DECISIONS = 20
MINIMUM_ABSOLUTE_POINTS = Decimal("0.05")
MINIMUM_RELATIVE_ERROR_REDUCTION = Decimal("0.20")


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required; source .env.s21d7.measured.local first")
    return value


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
            return SealedFeatureRecordSetV2.model_validate_json(path.read_text(encoding="utf-8"))
    raise SystemExit(f"the {partition} feature seal does not resolve in {store.name}")


def _catalogue_maps(catalogue: Any) -> tuple[dict, dict, dict, dict, dict]:
    order: dict[str, tuple[str, ...]] = {}
    delta: dict[str, str] = {}
    baseline: dict[str, str] = {}
    family: dict[str, str] = {}
    requirement: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[path]
        family[group.repository_group] = group.family
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for slot in group.slots:
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[
                RealityCandidateStrategy(slot.recipe)
            ][path]
    return order, delta, baseline, family, requirement


def _batch(
    partition: CorrectionPartition, ranker: ContainmentContrastiveRanker
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One final batch: every group's learned and deterministic first choice, and the ladder."""
    catalogue = seal_d7_corpus().catalogues[partition]
    seal = _sealed_records(D7_ARTIFACT_ROOT, FINAL_SEALS, partition.value)
    campaign = _read(FINAL_CAMPAIGN[partition])
    order, delta, baseline_source, family, requirement = _catalogue_maps(catalogue)

    rows = tuple(
        FittedRow(
            candidate_id=UUID(str(item["candidate_id"])),
            task_id=UUID(str(item["task_id"])),
            group=str(item["group"]),
            partition="final",
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
        for item in campaign["candidate_outcomes"]
    )
    matrix = FittedMatrix(split="calibration", rows=rows)

    ladder = build_ladder(
        matrix,
        order=order,
        requirement_texts=requirement,
        delta_texts=delta,
        created_at=seal.sealed_at,
    )
    strongest = ladder.strongest_non_learned_name
    ordering = eligible_rungs(matrix.rows[0].vector.encoder_version)[strongest]
    rung_first = {
        item.group: ordering(item)[0]
        for item in ladder_groups(
            matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }

    values: dict[str, dict[str, Any]] = {}
    accepted: dict[str, dict[str, bool]] = {}
    for row in matrix.rows:
        values.setdefault(row.group, {})[str(row.candidate_id)] = row.vector.values
        accepted.setdefault(row.group, {})[str(row.candidate_id)] = row.accepted

    decisions: list[dict[str, Any]] = []
    for name in sorted(order):
        numbers = relational_numbers(
            values[name],
            baseline_source=baseline_source[name],
            sources_by_candidate={item: delta[item] for item in order[name]},
        )
        ranking = ranker.rank(numbers, baseline_order=order[name])
        learned = ranking.ordered_candidate_ids[0]
        decisions.append(
            {
                "batch": partition.value,
                "group": name,
                "family": family[name],
                "margin": str(ranking.confidence),
                "learned_first": learned,
                "rung_first": rung_first[name],
                "learned_correct": bool(accepted[name][learned]),
                "rung_correct": bool(accepted[name][rung_first[name]]),
                "changed": learned != rung_first[name],
            }
        )
    report = {
        "batch": partition.value,
        "groups": len(decisions),
        "outcomes": len(matrix.rows),
        "matrix_hash": matrix.content_hash,
        "feature_seal_hash": seal.content_hash,
        "campaign_sha256": _digest(FINAL_CAMPAIGN[partition].read_bytes()),
        "strongest_rung": strongest,
        "strongest_rung_rate": ladder.strongest_non_learned_rate,
        "rungs": [json.loads(rung.model_dump_json()) for rung in ladder.rungs],
    }
    return decisions, report


def _rates(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(decisions)
    learned = sum(1 for item in decisions if item["learned_correct"])
    rung = sum(1 for item in decisions if item["rung_correct"])
    learned_rate = Decimal(learned) / Decimal(total)
    rung_rate = Decimal(rung) / Decimal(total)
    learned_error = Decimal(1) - learned_rate
    rung_error = Decimal(1) - rung_rate
    relative = (rung_error - learned_error) / rung_error if rung_error > 0 else None
    return {
        "decisions": total,
        "learned_first_choice": learned,
        "learned_first_choice_rate": str(learned_rate),
        "baseline_first_choice": rung,
        "baseline_first_choice_rate": str(rung_rate),
        "absolute_points_gained": str(learned_rate - rung_rate),
        "learned_error_rate": str(learned_error),
        "baseline_error_rate": str(rung_error),
        "relative_error_reduction": None if relative is None else str(relative),
        "direction_is_positive": learned_rate > rung_rate,
        "changed_decisions": sum(1 for item in decisions if item["changed"]),
    }


def _bootstrap(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    """Paired over groups: each resample redraws whole groups, keeping both answers together."""
    paired = [int(item["learned_correct"]) - int(item["rung_correct"]) for item in decisions]
    rng = random.Random(BOOTSTRAP_SEED)
    size = len(paired)
    draws = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        total = 0
        for _ in range(size):
            total += paired[rng.randrange(size)]
        draws.append(total / size)
    draws.sort()
    lower = draws[int(0.025 * BOOTSTRAP_RESAMPLES)]
    upper = draws[min(int(0.975 * BOOTSTRAP_RESAMPLES), BOOTSTRAP_RESAMPLES - 1)]
    observed = sum(paired) / size
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "unit": "group",
        "paired": True,
        "observed_difference": f"{observed:.6f}",
        "percentile_interval_95": [f"{lower:.6f}", f"{upper:.6f}"],
        "interval_excludes_zero": lower > 0 or upper < 0,
        "groups_where_only_the_learned_answer_is_right": sum(1 for item in paired if item > 0),
        "groups_where_only_the_baseline_answer_is_right": sum(1 for item in paired if item < 0),
        "why_groups_and_not_decisions": (
            "the two orderings answer the same groups, so the quantity with a distribution is "
            "the per-group difference; resampling decisions independently would break the "
            "pairing that makes the comparison sharp"
        ),
    }


def _shadow(
    record: dict[str, Any], decisions: list[dict[str, Any]], embedding: EmbeddingIdentity
) -> dict[str, Any]:
    """The ledger row in SHADOW: the learned ordering is computed and acts on nothing."""
    component = record["artifact"]["component_id"]
    manifest = _digest(b"d7-routing-manifest")
    policy = RoutingPolicy(
        persistence_enabled=True,
        activation_enabled=True,
        active_components=(component,),
        routed_groups=tuple(item["group"] for item in decisions),
        routing_manifest_hash=manifest,
    )
    state = ActiveComponentState(
        component_id=component,
        surface=record["artifact"]["surface"],
        revision=record["artifact"]["component_revision"],
        model_artifact_id=UUID(record["artifact"]["artifact_id"]),
        lineage_verified=True,
        descriptor_revision=record["artifact"]["component_revision"],
        lifecycle_state=LearnedComponentState.SHADOW,
    )
    resolver = LearnedRuntimeResolver(
        surface=record["artifact"]["surface"], expected_embedding=embedding
    )
    executed_changes = 0
    would_have_changed = 0
    reasons = set()
    for item in decisions:
        resolved = resolver.resolve(
            policy=policy,
            active_states=[state],
            group=item["group"],
            artifact=ArtifactAvailability(
                present=True, size_bytes=record["artifact"]["artifact_bytes"]
            ),
            local_embedding=embedding,
            expected_routing_manifest_hash=manifest,
        )
        reasons.add(resolved.reason.value)
        executed = (
            item["learned_first"] if resolved.learned_ordering_permitted else item["rung_first"]
        )
        executed_changes += int(executed != item["rung_first"])
        would_have_changed += int(item["changed"])
    return {
        "lifecycle_state": LearnedComponentState.SHADOW.value,
        "decisions": len(decisions),
        "resolver_reasons": sorted(reasons),
        "learned_ordering_permitted_anywhere": RuntimeHealthReason.ACTIVE.value in reasons,
        "executed_decisions_changed": executed_changes,
        "decisions_the_learned_ordering_would_have_changed": would_have_changed,
        "reading": (
            f"the learned ordering was computed for all {len(decisions)} final groups and "
            f"would have moved {would_have_changed} of them. The runtime executed none of "
            "that: with the ledger row in shadow the resolver refuses the learned path before "
            "any ordering is consulted, so what ran is the deterministic rung on every group"
        ),
        "why_this_is_the_claim": (
            "shadow is a statement about what executed, not about what was computed. A record "
            "showing only that nothing changed would be satisfied by a component that was never "
            "evaluated at all, so both numbers are here"
        ),
    }


async def _run(output: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    record = _read(ARTIFACT)
    contract = CorrectionFeatureContractV2()

    engine = create_postgres_engine(database_url)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        data = await artifacts.get_bytes(UUID(record["artifact"]["artifact_id"]))
    finally:
        await engine.dispose()
    if _digest(data) != record["artifact"]["artifact_hash"]:
        raise SystemExit("the stored artifact does not hash to what S21D7-036 recorded")

    capability = DirectEvaluationCapability(
        purpose=EvaluationPurpose.FINAL,
        component_state=LearnedComponentState.REGISTERED,
        artifact_hash=record["artifact"]["artifact_hash"],
        component_id=record["artifact"]["component_id"],
        component_revision=record["artifact"]["component_revision"],
        surface=record["artifact"]["surface"],
        descriptor_hash=record["artifact"]["descriptor_hash"],
        training_dataset_id=UUID(record["lineage"]["training_dataset_id"]),
        split_manifest_hash=record["lineage"]["split_manifest_hash"],
        member_manifest_hash=record["lineage"]["example_manifest_hash"],
        selection_manifest_hash=record["lineage"]["selection_manifest_hash"],
    )
    ranker, payload = build_ranker_for_evaluation_v3(data, capability=capability, contract=contract)
    if not isinstance(ranker, ContainmentContrastiveRanker):
        raise SystemExit("the artifact rebuilt into another class")

    batches = {}
    reports = {}
    for partition in (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B):
        batches[partition.value], reports[partition.value] = _batch(partition, ranker)
    pooled = [item for name in sorted(batches) for item in batches[name]]

    per_batch = {name: _rates(batches[name]) for name in sorted(batches)}
    overall = _rates(pooled)
    bootstrap = {
        "pooled": _bootstrap(pooled),
        **{name: _bootstrap(batches[name]) for name in sorted(batches)},
    }
    embedding = EmbeddingIdentity(
        model_id=payload.embedding_model_id, revision=payload.embedding_revision, available=True
    )
    shadow = _shadow(record, pooled, embedding)

    absolute = Decimal(overall["absolute_points_gained"])
    relative = (
        None
        if overall["relative_error_reduction"] is None
        else Decimal(overall["relative_error_reduction"])
    )
    conditions = {
        "13": {
            "asks": "at least 20 final group decisions differing from the strongest baseline",
            "measured": overall["changed_decisions"],
            "floor": MINIMUM_CHANGED_FINAL_DECISIONS,
            "met": overall["changed_decisions"] >= MINIMUM_CHANGED_FINAL_DECISIONS,
        },
        "14": {
            "asks": "at least 5 absolute points or 20% relative error reduction",
            "absolute_points": overall["absolute_points_gained"],
            "relative_error_reduction": overall["relative_error_reduction"],
            "met": bool(
                absolute >= MINIMUM_ABSOLUTE_POINTS
                or (relative is not None and relative >= MINIMUM_RELATIVE_ERROR_REDUCTION)
            ),
            "which_arm": (
                "absolute"
                if absolute >= MINIMUM_ABSOLUTE_POINTS
                else ("relative" if relative is not None and relative >= Decimal("0.20") else None)
            ),
        },
        "15": {
            "asks": "the paired group bootstrap over the final batches",
            "reported": sorted(bootstrap),
            "pooled_interval": bootstrap["pooled"]["percentile_interval_95"],
            "excludes_zero": bootstrap["pooled"]["interval_excludes_zero"],
            "met": True,
        },
        "16": {
            "asks": "a positive learned-minus-baseline direction in both final batches",
            "final_a": per_batch["final_a"]["absolute_points_gained"],
            "final_b": per_batch["final_b"]["absolute_points_gained"],
            "met": all(item["direction_is_positive"] for item in per_batch.values()),
        },
        "21": {
            "asks": "shadow mode changing zero executed decisions against final evidence",
            "executed_decisions_changed": shadow["executed_decisions_changed"],
            "met": shadow["executed_decisions_changed"] == 0,
        },
    }

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W3",
            "items": ["S21D7-039"],
            "final_outcomes_inspected": True,
            "final_or_canary_outcomes_inspected": len(pooled) * 4,
            "canary_outcomes_inspected": 0,
            "stores_opened_for_writing": 0,
            "conformal_bars_derived": 0,
            "directions_fitted": 0,
            "why_final_outcomes_are_read_here": (
                "this is the record that opens them. Condition 11 required the artifact to be "
                "selected first and S21D7-035 sealed it before the final roles were touched; "
                "from here the final evidence is spent"
            ),
            "inputs": {
                "artifact_sha256": _digest(ARTIFACT.read_bytes()),
                "final_feature_seals_sha256": _digest(FINAL_SEALS.read_bytes()),
                "final_a_campaign_sha256": _digest(
                    FINAL_CAMPAIGN[CorrectionPartition.FINAL_A].read_bytes()
                ),
                "final_b_campaign_sha256": _digest(
                    FINAL_CAMPAIGN[CorrectionPartition.FINAL_B].read_bytes()
                ),
                "final_role_audit_sha256": _digest(FINAL_ROLE_AUDIT.read_bytes()),
                "learner_selection_sha256": _digest(SELECTION.read_bytes()),
            },
            "artifact": {
                "artifact_hash": record["artifact"]["artifact_hash"],
                "model_hash": ranker.model.content_hash(),
                "rebuilt_through_the_evaluation_boundary": True,
                "purpose": EvaluationPurpose.FINAL.value,
                "why_not_a_re_fit": (
                    "a gain measured with a freshly fitted direction would be a claim about the "
                    "fitting code. These numbers are the promoted bytes'"
                ),
            },
            "batches": reports,
            "decisions": pooled,
            "per_batch": per_batch,
            "overall": overall,
            "bootstrap": bootstrap,
            "shadow": shadow,
            "conditions": conditions,
            "all_conditions_met": all(item["met"] for item in conditions.values()),
            "what_this_record_is_not": (
                "a second selection. The candidate was selected under §2.3 on the certification "
                "half and bound before any final manifest was opened; these numbers confirm or "
                "refute it on unread evidence and cannot re-choose it"
            ),
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
                "groups": overall["decisions"],
                "learned_rate": overall["learned_first_choice_rate"],
                "baseline": {
                    name: [
                        reports[name]["strongest_rung"],
                        reports[name]["strongest_rung_rate"],
                    ]
                    for name in reports
                },
                "absolute_points": overall["absolute_points_gained"],
                "relative_error_reduction": overall["relative_error_reduction"],
                "changed_decisions": overall["changed_decisions"],
                "bootstrap_95": bootstrap["pooled"]["percentile_interval_95"],
                "per_batch_direction": {
                    name: per_batch[name]["absolute_points_gained"] for name in per_batch
                },
                "shadow_executed_changes": shadow["executed_decisions_changed"],
                "conditions_met": {name: conditions[name]["met"] for name in sorted(conditions)},
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if evidence["all_conditions_met"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return asyncio.run(_run(parser.parse_args().output))


if __name__ == "__main__":
    raise SystemExit(main())
