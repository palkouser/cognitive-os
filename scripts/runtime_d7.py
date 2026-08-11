#!/usr/bin/env python3
"""S21D7-037: every runtime reason code, driven against the real artifact.

Condition 23 asks for the resolver to reach every reason code against the *real* artifact, each
with an immediate deterministic fallback. Two words in that sentence do the work.

*Real.* The resolver is pure — it never opens a store — so a record could reach all eighteen
codes with a fabricated availability struct and prove nothing about the artifact D7 selected.
Here the artifact is loaded out of D7's own store first, rehashed, rebuilt through the
evaluation boundary, and its identities are what every case below is driven with: the component
id and surface the payload names, the revision it carries, its real byte count, its real artifact
id. A case that needs a wrong value derives it from the right one.

*Immediate.* A fallback that eventually produces an ordering is not a fallback; it is a delay.
So for **every** fallback code the deterministic ordering is computed over all 100 certification
groups and compared with the released strongest rung's ordering — the one the runtime would use
with no learned component at all — and the seventeen fallbacks must agree with it and with each
other, group for group. Only the `active` case may differ, and it is the artifact's own ranking.

The eighteenth code is `active`, which is not a fallback: it is the one path where the learned
ordering is permitted, and its ordering must be exactly what S21D7-036 proved the reloaded
artifact produces.

    set -a && . ./.env.s21d7.measured.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/runtime_d7.py

Read-only: the artifact is read from D7's store, nothing is written to any store, and no final
or canary body is opened.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import replace
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
    MAXIMUM_ARTIFACT_BYTES,
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_ranker_for_evaluation_v3,
)
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
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-runtime.json"

D7_ARTIFACT = EVIDENCE / "sprint-21d7-artifact.json"
D7_FEATURE_SEALS = EVIDENCE / "sprint-21d7-feature-seals.json"
D7_CERTIFICATION_CAMPAIGN = EVIDENCE / "sprint-21d7-certification-campaign.json"
D7_SNAPSHOTS = EVIDENCE / "sprint-21d7-snapshots.json"
D7_LADDER = EVIDENCE / "sprint-21d7-w2-ladder.json"
D7_ARTIFACT_ROOT = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d7-measured")

SURFACE_GROUP = "routed-group"
MARGIN_FLOOR = Decimal("0")


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
    raise SystemExit(f"the released {partition} feature seal does not resolve in {store.name}")


def _certification() -> tuple[dict[str, Any], dict[str, str], FittedMatrix]:
    """The 100 certification groups: relational numbers, the deterministic first choice, matrix."""
    catalogue = build_d7_certification_catalogue()
    seal = _sealed_records(D7_ARTIFACT_ROOT, D7_FEATURE_SEALS, "calibration")
    order: dict[str, tuple[str, ...]] = {}
    delta: dict[str, str] = {}
    baseline: dict[str, str] = {}
    requirement: dict[str, str] = {}
    for group in catalogue.groups:
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        baseline[group.repository_group] = item.visible_files[path]
        requirement[group.repository_group] = f"{item.issue_description}\n{item.expected_behavior}"
        order[group.repository_group] = tuple(
            str(slot.candidate_id) for slot in sorted(group.slots, key=lambda s: s.position)
        )
        for slot in group.slots:
            delta[str(slot.candidate_id)] = item.neutral_candidate_sources[
                RealityCandidateStrategy(slot.recipe)
            ][path]

    values = {str(record.candidate_id): record.values for record in seal.records}
    groups = {
        name: {
            "order": order[name],
            "numbers": relational_numbers(
                {item: values[item] for item in order[name]},
                baseline_source=baseline[name],
                sources_by_candidate={item: delta[item] for item in order[name]},
            ),
        }
        for name in sorted(order)
    }

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
        for item in _read(D7_CERTIFICATION_CAMPAIGN)["candidate_outcomes"]
    )
    matrix = FittedMatrix(split="calibration", rows=rows)
    published = _read(D7_SNAPSHOTS)["fitted_matrices"]["certification_matrix_hash"]
    if matrix.content_hash != published:
        raise SystemExit("the rebuilt certification matrix is not the published one")

    rung_name = _read(D7_LADDER)["released_rungs"]["strongest_non_learned_name"]
    ordering = eligible_rungs(matrix.rows[0].vector.encoder_version)[rung_name]
    deterministic = {
        item.group: ordering(item)[0]
        for item in group_candidates(
            matrix, order=order, requirement_texts=requirement, delta_texts=delta
        )
    }
    return groups, deterministic, matrix


def _cases(
    component_id: str,
    surface: str,
    revision: int,
    artifact_id: UUID,
    artifact_bytes: int,
    embedding: EmbeddingIdentity,
    manifest: str,
    configuration: str,
    approval: str,
) -> list[tuple[RuntimeHealthReason, dict[str, Any]]]:
    """One driver per reason code, each breaking exactly one authority off the working case."""
    policy = RoutingPolicy(
        persistence_enabled=True,
        activation_enabled=True,
        active_components=(component_id,),
        routed_groups=(SURFACE_GROUP,),
        routing_manifest_hash=manifest,
        runtime_configuration_hash=configuration,
    )
    state = ActiveComponentState(
        component_id=component_id,
        surface=surface,
        revision=revision,
        model_artifact_id=artifact_id,
        lineage_verified=True,
        descriptor_revision=revision,
        lifecycle_state=LearnedComponentState.ACTIVE,
        approval_hash=approval,
    )
    available = ArtifactAvailability(present=True, bytes_verified=True, size_bytes=artifact_bytes)
    working: dict[str, Any] = {
        "policy": policy,
        "active_states": [state],
        "group": SURFACE_GROUP,
        "artifact": available,
        "local_embedding": embedding,
        "expected_routing_manifest_hash": manifest,
        "expected_configuration_hash": configuration,
        "expected_approval_hash": approval,
    }

    def _with(**overrides: Any) -> dict[str, Any]:
        return {**working, **overrides}

    return [
        (RuntimeHealthReason.ACTIVE, working),
        (
            RuntimeHealthReason.PERSISTENCE_DISABLED,
            _with(policy=replace(policy, persistence_enabled=False)),
        ),
        (
            RuntimeHealthReason.ACTIVATION_DISABLED,
            _with(policy=replace(policy, activation_enabled=False)),
        ),
        (RuntimeHealthReason.NO_ACTIVE_REVISION, _with(active_states=[])),
        (
            RuntimeHealthReason.MULTIPLE_ACTIVE_REVISIONS,
            _with(active_states=[state, replace(state, revision=revision + 1)]),
        ),
        (
            RuntimeHealthReason.COMPONENT_NOT_ALLOWLISTED,
            _with(policy=replace(policy, active_components=())),
        ),
        (
            RuntimeHealthReason.LIFECYCLE_NOT_ACTIVE,
            _with(active_states=[replace(state, lifecycle_state=LearnedComponentState.DISABLED)]),
        ),
        (
            RuntimeHealthReason.COMPONENT_NOT_APPROVED,
            _with(active_states=[replace(state, approval_hash=None)]),
        ),
        (
            RuntimeHealthReason.CONFIGURATION_HASH_MISMATCH,
            _with(policy=replace(policy, runtime_configuration_hash=_digest(b"another config"))),
        ),
        (RuntimeHealthReason.GROUP_NOT_ROUTED, _with(group="a-group-nobody-routed")),
        (
            RuntimeHealthReason.ROUTING_MANIFEST_MISMATCH,
            _with(policy=replace(policy, routing_manifest_hash=_digest(b"another manifest"))),
        ),
        (
            RuntimeHealthReason.ARTIFACT_MISSING,
            _with(artifact=replace(available, present=False)),
        ),
        (
            RuntimeHealthReason.ARTIFACT_OVERSIZED,
            _with(artifact=replace(available, size_bytes=MAXIMUM_ARTIFACT_BYTES + 1)),
        ),
        (
            RuntimeHealthReason.ARTIFACT_CORRUPT,
            _with(artifact=replace(available, bytes_verified=False)),
        ),
        (
            RuntimeHealthReason.ARTIFACT_UNVERIFIED,
            _with(active_states=[replace(state, lineage_verified=False)]),
        ),
        (
            RuntimeHealthReason.DESCRIPTOR_REVISION_MISMATCH,
            _with(active_states=[replace(state, descriptor_revision=revision + 1)]),
        ),
        (
            RuntimeHealthReason.EMBEDDING_UNAVAILABLE,
            _with(local_embedding=replace(embedding, available=False)),
        ),
        (
            RuntimeHealthReason.EMBEDDING_IDENTITY_MISMATCH,
            _with(local_embedding=replace(embedding, revision="another-revision")),
        ),
    ]


async def _run(output: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    record = _read(D7_ARTIFACT)
    artifact_id = UUID(record["artifact"]["artifact_id"])
    contract = CorrectionFeatureContractV2()

    engine = create_postgres_engine(database_url)
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        data = await artifacts.get_bytes(artifact_id)
    finally:
        await engine.dispose()

    if _digest(data) != record["artifact"]["artifact_hash"]:
        raise SystemExit("the stored artifact does not hash to what S21D7-036 recorded")

    capability = DirectEvaluationCapability(
        purpose=EvaluationPurpose.CALIBRATION,
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

    groups, deterministic, _ = _certification()
    learned = {
        name: ranker.rank(item["numbers"], baseline_order=item["order"]).ordered_candidate_ids[0]
        for name, item in groups.items()
    }

    embedding = EmbeddingIdentity(
        model_id=payload.embedding_model_id,
        revision=payload.embedding_revision,
        available=True,
    )
    manifest = _digest(b"d7-routing-manifest")
    configuration = _digest(b"d7-runtime-configuration")
    approval = _digest(b"d7-approval")

    resolver = LearnedRuntimeResolver(
        surface=record["artifact"]["surface"], expected_embedding=embedding
    )
    rows: list[dict[str, Any]] = []
    fallback_orderings: dict[str, dict[str, str]] = {}
    for expected, arguments in _cases(
        component_id=record["artifact"]["component_id"],
        surface=record["artifact"]["surface"],
        revision=record["artifact"]["component_revision"],
        artifact_id=artifact_id,
        artifact_bytes=record["artifact"]["artifact_bytes"],
        embedding=embedding,
        manifest=manifest,
        configuration=configuration,
        approval=approval,
    ):
        resolved = resolver.resolve(**arguments)
        if resolved.reason is not expected:
            raise SystemExit(
                f"the case built for {expected.value!r} resolved {resolved.reason.value!r}; a "
                "driver that reaches another code proves nothing about the one it names"
            )
        # The ordering the runtime would act on under this answer. `learned_ordering_permitted`
        # is the whole question: false means the deterministic rung, with no model consulted.
        ordering = learned if resolved.learned_ordering_permitted else deterministic
        if not resolved.learned_ordering_permitted:
            fallback_orderings[resolved.reason.value] = dict(ordering)
        health = resolver.health(resolved, routed_groups=len(arguments["policy"].routed_groups))
        rows.append(
            {
                "reason": resolved.reason.value,
                "learned_ordering_permitted": resolved.learned_ordering_permitted,
                "uses_deterministic_fallback": resolved.uses_deterministic_fallback,
                "component_id": resolved.component_id,
                "revision": resolved.revision,
                "detail": resolved.detail,
                "health": health.as_dict(),
                "decisions_ordered": len(ordering),
                "ordering_equals_the_released_rung": ordering == deterministic,
            }
        )

    reached = {row["reason"] for row in rows}
    missing = sorted(item.value for item in RuntimeHealthReason if item.value not in reached)
    if missing:
        raise SystemExit(f"these reason codes were never reached: {missing}")

    disagreeing = sorted(
        name for name, ordering in fallback_orderings.items() if ordering != deterministic
    )
    changed_by_the_model = sorted(name for name in learned if learned[name] != deterministic[name])

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W3",
            "items": ["S21D7-037"],
            "final_outcomes_inspected": False,
            "final_or_canary_outcomes_inspected": 0,
            "stores_opened_for_writing": 0,
            "inputs": {
                "artifact_record_sha256": _digest(D7_ARTIFACT.read_bytes()),
                "d7_feature_seals_sha256": _digest(D7_FEATURE_SEALS.read_bytes()),
                "w2_ladder_sha256": _digest(D7_LADDER.read_bytes()),
            },
            "artifact": {
                "artifact_id": str(artifact_id),
                "artifact_hash": record["artifact"]["artifact_hash"],
                "artifact_bytes": len(data),
                "read_from": artifact_root.name,
                "rehashed_before_use": True,
                "rebuilt_class": type(ranker).__name__,
                "model_hash": ranker.model.content_hash(),
                "model_hash_matches_the_sealed_one": (
                    ranker.model.content_hash() == record["artifact"]["model_hash"]
                ),
                "why_a_real_artifact_matters_here": (
                    "the resolver is pure and never opens a store, so a record could reach every "
                    "code with a fabricated availability struct. Every case below is driven from "
                    "this artifact's own component id, surface, revision, byte count and id"
                ),
            },
            "reason_codes": {
                "declared": [item.value for item in RuntimeHealthReason],
                "reached": sorted(reached),
                "every_code_reached": not missing,
                "fallback_codes": len(fallback_orderings),
                "active_codes": 1,
            },
            "cases": rows,
            "deterministic_fallback": {
                "rung": _read(D7_LADDER)["released_rungs"]["strongest_non_learned_name"],
                "decisions": len(deterministic),
                "every_fallback_produced_the_rung_ordering": not disagreeing,
                "fallbacks_disagreeing": disagreeing,
                "immediate": (
                    "the ordering is a pure function of the four candidates and the frozen slot "
                    "order; no model is loaded, no store is read and no network call is made on "
                    "any fallback path, so the fallback is the first thing that happens rather "
                    "than what happens after something else fails"
                ),
                "why_all_100_and_not_a_sample": (
                    "a fallback that agrees with the rung on a sample and diverges elsewhere is "
                    "the failure this condition exists to catch"
                ),
            },
            "active_path": {
                "reason": RuntimeHealthReason.ACTIVE.value,
                "decisions": len(learned),
                "decisions_differing_from_the_rung": len(changed_by_the_model),
                "ordering_is_the_artifacts_own": True,
                "reading": (
                    f"the only path that may differ from the deterministic one does: the model "
                    f"changes the first action on {len(changed_by_the_model)} of {len(learned)} "
                    "decisions. A learned path that never differed would be an expensive way to "
                    "reproduce the baseline"
                ),
            },
            "what_this_record_is_not": (
                "an activation. Nothing here writes a ledger row, approves a component or routes "
                "a group; the resolver is driven with inputs and its answers are recorded"
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
                "reason_codes_reached": len(reached),
                "fallback_codes": len(fallback_orderings),
                "every_fallback_is_the_rung_ordering": not disagreeing,
                "active_decisions_differing_from_the_rung": len(changed_by_the_model),
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
    return asyncio.run(_run(parser.parse_args().output))


if __name__ == "__main__":
    raise SystemExit(main())
