#!/usr/bin/env python3
"""S21D4-023. The v2 seal, dataset, receipt and restart spine, at Sprint 21D4's campaign shape.

Sprint 21D3 proved this spine on one task with four candidates. That was enough to show the
mechanism exists and not enough to show it survives the campaign D4 actually intends to run: two
partitions, a hundred and eighty tasks, seven hundred and twenty candidates, and a restart in the
middle of none of it. Sizes are not a detail here — a dataset identity that is stable over four
members and unstable over four hundred is a dataset identity nobody can restart against.

Four properties, each of which is a way the campaign could quietly lose its meaning:

*Features are sealed strictly before any outcome exists.* Otherwise the encoder has seen the
label. The refusal is exercised, not asserted: a second seal is attempted with an outcome already
in hand and must be rejected.

*Execution is receipt-bound.* A candidate that was deliberately not attempted and a candidate
that was never reached look identical in an outcome stream, and under stop-on-first-accept they
are different experiments.

*Restart reproduces identity.* Fresh application services over the same durable authorities must
rebuild the same dataset record, the same split and example manifests, and the same seal time —
the stored one, not the restart's clock.

*The effective remainder is empty.* A completed partition that resumes with work to do would
re-run candidates that already have outcomes, under the same campaign identity.

Every group here is a fixture group. None of them is a D4 fitting, calibration, final, promotion
or canary member, and the identifiers say so, because a spine proof that borrowed a real group
would spend it.

    UV_CACHE_DIR=.cache/uv uv run python scripts/seal_resume_d4.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.learned_datasets import (  # noqa: E402
    DATASET_NAMESPACE,
    ExplicitSelection,
    LearnedDatasetBuilder,
)
from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    RealityCampaignLedger,
)
from cognitive_os.domain.common import ArtifactRef  # noqa: E402
from cognitive_os.domain.enums import StreamType  # noqa: E402
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass  # noqa: E402
from cognitive_os.domain.learned_evidence import (  # noqa: E402
    LearnedArtifactRole,
    LearnedObservationRecord,
    ObservationAttribution,
    ObservationStatus,
)
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCampaignManifest,
    RealityCampaignReceiptManifestV3,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityReceiptTaskV3,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.events.coding_events import (  # noqa: E402
    CodingOutcomeRecorded,
    RealityCampaignSequenceRecorded,
)
from cognitive_os.events.memory_store import MemoryEventStore  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore  # noqa: E402
from cognitive_os.infrastructure.learned.memory_repository import (  # noqa: E402
    InMemoryLearnedEvidenceRepository,
)
from cognitive_os.learning.correction_features import (  # noqa: E402
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
    feature_input_v2,
    raw_numeric_row_v2,
    seal_feature_records_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    DecisionCensusV4,
)
from cognitive_os.learning.correction_ranking import NumericBoundsV2  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SURFACE = "experience.correction_ranking"
SEALED_AT = datetime(2026, 8, 6, 9, tzinfo=UTC)
OUTCOME_AT = SEALED_AT + timedelta(hours=1)
RECORDED_AT = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

#: S21D4-012's two volumes, as a campaign shape: 80 fitting groups and 100 calibration groups,
#: four candidates each. `CorpusRole` stays two-valued, so the calibration partition carries the
#: evaluation role — the partition name is what distinguishes them, exactly as in D2 and D3.
PARTITIONS: tuple[tuple[str, CorpusRole, int], ...] = (
    ("training", CorpusRole.TRAINING, 80),
    ("calibration", CorpusRole.EVALUATION, 100),
)

STRATEGIES = (
    RealityCandidateStrategy.RECIPE_ALPHA,
    RealityCandidateStrategy.RECIPE_BETA,
    RealityCandidateStrategy.RECIPE_GAMMA,
    RealityCandidateStrategy.RECIPE_DELTA,
)

#: Four distinct bodies per group, varied by group so no two groups encode alike. A fixture whose
#: groups collapsed onto one fitted vector would prove the spine on one decision, which is the
#: mistake this sprint exists to correct.
CANDIDATE_SHAPES = (
    "def bound_{index}(value):\n    return max({low}, min({high}, value))\n",
    "def bound_{index}(value):\n    return {low} if value < {low} else min({high}, value)\n",
    "def bound_{index}(value):\n    return min({high}, max(value, {low}))\n",
    "def bound_{index}(value):\n    if value < {low}:\n        return {low}\n"
    "    return min(value, {high})\n",
)

IMPLEMENTATION_FILES = (
    REPOSITORY / "src/cognitive_os/learning/correction_source.py",
    REPOSITORY / "src/cognitive_os/learning/correction_features.py",
    REPOSITORY / "src/cognitive_os/learning/correction_ranking.py",
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


def _implementation_digest() -> str:
    digest = sha256()
    for path in IMPLEMENTATION_FILES:
        digest.update(path.relative_to(REPOSITORY).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _embedding(seed: int) -> tuple[float, ...]:
    return tuple(((index + seed) % 19 - 9) / 10 for index in range(384))


def _sources(partition: str, group: int) -> tuple[str, ...]:
    low, high = group % 7, 10 + (group % 11)
    return tuple(
        shape.format(index=f"{partition}_{group}", low=low, high=high) for shape in CANDIDATE_SHAPES
    )


class _ArtifactAuthority:
    """Real content-addressed bytes with deterministic in-memory metadata for this fixture."""

    def __init__(self, root: Path) -> None:
        self.files = ContentAddressedFilesystem(root)
        self.references: dict[UUID, ArtifactRef] = {}

    async def put_bytes(
        self, data: bytes, *, media_type: str, source_event_id: UUID | None = None
    ) -> ArtifactRef:
        del source_event_id
        blob = self.files.put_bytes(data)
        artifact_id = uuid5(NAMESPACE_URL, f"cogos:d4-w1-artifact:{blob.content_hash}")
        reference = ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=blob.content_hash,
            size_bytes=blob.size_bytes,
            storage_key=blob.storage_key,
            created_at=SEALED_AT,
        )
        self.references[artifact_id] = reference
        return reference

    async def describe(self, artifact_id: UUID) -> ArtifactRef | None:
        return self.references.get(artifact_id)

    async def verify(self, artifact_id: UUID) -> bool:
        reference = self.references[artifact_id]
        return self.files.verify_blob(
            reference.storage_key, reference.content_hash, reference.size_bytes
        )


async def _run_partition(
    *,
    partition: str,
    corpus_role: CorpusRole,
    groups: int,
    authority: _ArtifactAuthority,
    code_revision: str,
) -> dict[str, Any]:
    """One partition, sealed before outcomes, executed, then rebuilt from scratch."""
    contract = CorrectionFeatureContractV2()
    campaign_id = uuid5(NAMESPACE_URL, f"cogos:d4-w1:campaign:{partition}")
    verifier_hash = _digest(f"d4-w1-verifier:{partition}")

    task_ids = [
        uuid5(NAMESPACE_URL, f"cogos:d4-w1:{partition}:task:{index}") for index in range(groups)
    ]
    task_manifest_hashes = {
        task_id: _digest(f"d4-w1-task:{partition}:{index}")
        for index, task_id in enumerate(task_ids)
    }
    candidates = {
        task_id: tuple(
            uuid5(NAMESPACE_URL, f"cogos:d4-w1:{partition}:{index}:candidate:{slot}")
            for slot in range(4)
        )
        for index, task_id in enumerate(task_ids)
    }
    sources = {task_id: _sources(partition, index) for index, task_id in enumerate(task_ids)}

    planned = tuple(
        RealityRunIdentity(
            task_id=task_id,
            task_manifest_hash=task_manifest_hashes[task_id],
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate_id,
            strategy=strategy,
            source=RealityCandidateSource.CURATED,
            generator_profile_id="d4-w1-fixture",
            verifier_profile_hash=verifier_hash,
            campaign_version=4,
        )
        for task_id in task_ids
        for candidate_id, strategy in zip(candidates[task_id], STRATEGIES, strict=True)
    )
    base_manifest = RealityCampaignManifest(
        campaign_id=campaign_id,
        campaign_version=4,
        planned_runs=planned,
        verifier_profile_hash=verifier_hash,
        created_at=SEALED_AT - timedelta(minutes=5),
    )

    raw = [
        raw_numeric_row_v2(
            feature_input_v2(
                candidate_source=source,
                canonical_candidate_source_embedding=_embedding(index * 4 + slot),
            )
        )
        for index, task_id in enumerate(task_ids)
        for slot, source in enumerate(sources[task_id])
    ]
    bounds = NumericBoundsV2.from_training(raw)
    pending = [
        PendingFeatureV2(
            candidate_id=candidate_id,
            task_id=task_id,
            repository_group=f"d4-w1-fixture-group-{partition}-{index}",
            candidate_source=sources[task_id][slot],
            canonical_candidate_source_embedding=_embedding(index * 4 + slot),
        )
        for index, task_id in enumerate(task_ids)
        for slot, candidate_id in enumerate(candidates[task_id])
    ]
    feature_seal = seal_feature_records_v2(
        pending,
        partition=partition,
        campaign_manifest_hash=base_manifest.content_hash,
        bounds=bounds,
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        embedding_tree_digest="98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229",
        code_revision=code_revision,
        sealed_at=SEALED_AT,
    )
    replayed_seal = SealedFeatureRecordSetV2.model_validate_json(feature_seal.canonical_json())
    if replayed_seal.content_hash != feature_seal.content_hash:
        raise RuntimeError(f"{partition}: serialized v2 feature seal did not reproduce")

    try:
        seal_feature_records_v2(
            pending,
            partition=partition,
            campaign_manifest_hash=base_manifest.content_hash,
            bounds=bounds,
            embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
            embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            embedding_tree_digest="98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229",
            code_revision=code_revision,
            sealed_at=OUTCOME_AT,
            earliest_outcome_at=OUTCOME_AT,
        )
    except ValueError as error:
        post_outcome_refusal = str(error)
    else:  # pragma: no cover - the fixture exists to make this impossible
        raise RuntimeError(f"{partition}: a post-outcome v2 feature seal was accepted")

    artifacts = LearnedArtifactStore(authority)
    repository = InMemoryLearnedEvidenceRepository()

    seal_reference = await artifacts.store(
        feature_seal.canonical_json().encode(), media_type="application/json"
    )
    seal_lineage = await artifacts.build_lineage(
        lineage_id=uuid5(NAMESPACE_URL, f"cogos:d4-w1:{partition}:seal-lineage"),
        artifact_id=seal_reference.artifact_id,
        role=LearnedArtifactRole.REPORT,
        declared_format="json",
        component_id="learned.knn.correction_ranking",
        producing_evidence_hash=feature_seal.content_hash,
        verified_by="s21d4-w1-fixture",
    )
    await repository.record_artifact_lineage(seal_lineage)

    observations: list[LearnedObservationRecord] = []
    outcome_references: dict[UUID, ArtifactRef] = {}
    hidden_references: dict[UUID, ArtifactRef] = {}
    observation_of: dict[UUID, LearnedObservationRecord] = {}
    ordinal = 0
    for task_id in task_ids:
        for candidate_id in candidates[task_id]:
            outcome = await artifacts.store(
                f"candidate={candidate_id};accepted=false\n".encode(),
                media_type="application/json",
            )
            hidden = await artifacts.store(
                f"candidate={candidate_id};hidden=false\n".encode(),
                media_type="application/json",
            )
            outcome_references[candidate_id] = outcome
            hidden_references[candidate_id] = hidden
            observation = await repository.record_observation(
                LearnedObservationRecord(
                    observation_id=uuid5(
                        NAMESPACE_URL, f"cogos:d4-w1:{partition}:observation:{ordinal}"
                    ),
                    surface=SURFACE,
                    source_kind="self_play_task_run",
                    source_task_id=task_id,
                    source_payload_hash=outcome.content_hash,
                    provenance_class=ProvenanceClass.SELF_PLAY,
                    attribution=ObservationAttribution.DIRECT,
                    status=ObservationStatus.ACCEPTED,
                    verifier_status="failed",
                    verifier_evidence_hash=hidden.content_hash,
                    usage_rights_verified=True,
                    sensitivity="internal",
                    decision_reason="deterministic W1 seal, receipt and restart fixture",
                    evaluation_eligible=True,
                    idempotency_key=f"s21d4-w1-{partition}-observation-{ordinal}",
                    recorded_at=OUTCOME_AT + timedelta(seconds=ordinal),
                )
            )
            observations.append(observation)
            observation_of[candidate_id] = observation
            ordinal += 1

    feature_hashes = {
        str(observation_of[candidate_id].observation_id): feature_seal.record_for(
            candidate_id
        ).content_hash
        for task_id in task_ids
        for candidate_id in candidates[task_id]
    }
    outcome_hashes = {
        str(observation_of[candidate_id].observation_id): outcome_references[
            candidate_id
        ].content_hash
        for task_id in task_ids
        for candidate_id in candidates[task_id]
    }
    member_hashes = {
        identity: _digest(f"{identity}:{feature_hashes[identity]}:{outcome_hashes[identity]}")
        for identity in feature_hashes
    }
    observation_ids = tuple(str(item.observation_id) for item in observations)
    groups_by_observation = {
        str(observation_of[candidate_id].observation_id): (
            f"d4-w1-fixture-group-{partition}-{index}"
        )
        for index, task_id in enumerate(task_ids)
        for candidate_id in candidates[task_id]
    }
    selection = ExplicitSelection(
        partition=partition,
        members=tuple(
            (str(item.observation_id), item.source_payload_hash) for item in observations
        ),
        groups=groups_by_observation,
        splits={"fit": observation_ids},
        allowed_provenance=ProvenanceClass.SELF_PLAY,
        identity_revision=3,
        campaign_identity=base_manifest.content_hash,
        feature_record_hashes=feature_hashes,
        outcome_hashes=outcome_hashes,
        member_content_hashes=member_hashes,
    )
    builder = LearnedDatasetBuilder(
        repository, artifacts, clock=lambda: OUTCOME_AT + timedelta(minutes=5)
    )
    dataset = await builder.build(
        surface=SURFACE,
        corpus_role=corpus_role,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )

    receipt_manifest = RealityCampaignReceiptManifestV3(
        **base_manifest.model_dump(exclude={"content_hash"}),
        partition=partition,
        mode="label_all",
        selection_manifest_hash=dataset.split_manifest_hash,
        feature_schema_hash=contract.content_hash,
        feature_seal_root_hash=feature_seal.content_hash,
        receipt_tasks=tuple(
            RealityReceiptTaskV3(
                task_id=task_id,
                task_manifest_hash=task_manifest_hashes[task_id],
                bundle_id=uuid5(NAMESPACE_URL, f"cogos:d4-w1:{partition}:bundle:{index}"),
                bundle_hash=_digest(f"d4-w1-bundle:{partition}:{index}"),
                feature_seal_hash=feature_seal.content_hash,
                candidate_order=candidates[task_id],
                selected_member_hashes=tuple(
                    member_hashes[str(observation_of[candidate_id].observation_id)]
                    for candidate_id in candidates[task_id]
                ),
            )
            for index, task_id in enumerate(task_ids)
        ),
    )

    event_store = MemoryEventStore()
    events = CodingEventService(event_store)
    task_run_ids: list[UUID] = []
    outcome_event_ids: list[UUID] = []
    for ordinal, identity in enumerate(planned):
        task_run_id = uuid5(NAMESPACE_URL, f"cogos:d4-w1:{partition}:task-run:{ordinal}")
        task_run_ids.append(task_run_id)
        outcome = outcome_references[identity.candidate_id]
        hidden = hidden_references[identity.candidate_id]
        outcome_event_ids.append(
            await events.append(
                task_run_id,
                CodingOutcomeRecorded(
                    task_run_id=task_run_id,
                    run_kind=RealityRunKind.CANDIDATE,
                    task_id=identity.task_id,
                    task_manifest_hash=identity.task_manifest_hash,
                    candidate_id=identity.candidate_id,
                    candidate_strategy=identity.strategy,
                    outcome_hash=outcome.content_hash,
                    outcome_artifact_id=outcome.artifact_id,
                    outcome_artifact_hash=outcome.content_hash,
                    hidden_evidence_artifact_id=hidden.artifact_id,
                    hidden_evidence_hash=hidden.content_hash,
                    final_status="failed",
                    hidden_verification_passed=False,
                    run_identity_key=identity.key,
                    occurred_at=OUTCOME_AT + timedelta(seconds=ordinal),
                ),
                correlation_id=campaign_id,
                stream_type=StreamType.TASK_RUN,
            )
        )
    sequence_event_ids: list[UUID] = []
    for index, task_id in enumerate(task_ids):
        sequence_event_ids.append(
            await events.append(
                campaign_id,
                RealityCampaignSequenceRecorded(
                    campaign_id=campaign_id,
                    task_id=task_id,
                    partition=partition,
                    mode="label_all",
                    campaign_manifest_hash=receipt_manifest.content_hash,
                    baseline_order=candidates[task_id],
                    resolved_order=candidates[task_id],
                    attempted_order=candidates[task_id],
                    intentionally_unattempted=(),
                    stop_reason="exhausted_without_acceptance",
                    occurred_at=OUTCOME_AT + timedelta(minutes=1, seconds=index),
                ),
                correlation_id=campaign_id,
                stream_type=StreamType.SYSTEM,
            )
        )

    # Restart: fresh application services over the same durable authorities.
    restarted_dataset = await LearnedDatasetBuilder(
        repository,
        LearnedArtifactStore(authority),
        clock=lambda: OUTCOME_AT + timedelta(days=1),
    ).build(
        surface=SURFACE,
        corpus_role=corpus_role,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )
    resumed = await RealityCampaignLedger(event_store).plan_resume_with_receipts(
        receipt_manifest, task_run_ids=task_run_ids, campaign_id=campaign_id
    )
    if restarted_dataset != dataset:
        raise RuntimeError(f"{partition}: restart did not reproduce the dataset record")
    if resumed.effective_remainder:
        raise RuntimeError(
            f"{partition}: {len(resumed.effective_remainder)} candidate(s) would be re-run"
        )
    receipt_members = tuple(
        member for task in receipt_manifest.receipt_tasks for member in task.selected_member_hashes
    )
    if sorted(receipt_members) != sorted(member_hashes.values()):
        raise RuntimeError(f"{partition}: receipt members no longer resolve the dataset selection")

    split_lineage = await repository.get_artifact_lineage(
        uuid5(DATASET_NAMESPACE, f"{dataset.dataset_id}|{LearnedArtifactRole.SPLIT_MANIFEST.value}")
    )
    example_lineage = await repository.get_artifact_lineage(
        uuid5(
            DATASET_NAMESPACE, f"{dataset.dataset_id}|{LearnedArtifactRole.EXAMPLE_MANIFEST.value}"
        )
    )
    if split_lineage is None or example_lineage is None:
        raise RuntimeError(f"{partition}: dataset manifest lineage did not survive restart")

    census = DecisionCensusV4.from_feature_hashes(sorted(feature_hashes.values()))

    return {
        "partition": partition,
        "corpus_role": corpus_role.value,
        "groups": groups,
        "candidate_outcomes": groups * 4,
        "fixture_group_prefix": f"d4-w1-fixture-group-{partition}-",
        "census": census.model_dump(mode="json", exclude={"content_hash", "independence_rule"}),
        "chronology": {
            "base_manifest_created_at": base_manifest.created_at.isoformat(),
            "features_sealed_at": feature_seal.sealed_at.isoformat(),
            "first_outcome_at": OUTCOME_AT.isoformat(),
            "strictly_pre_outcome": feature_seal.sealed_at < OUTCOME_AT,
            "stored_seal_time_preserved": replayed_seal.sealed_at == feature_seal.sealed_at,
            "post_outcome_seal_refusal": post_outcome_refusal,
        },
        "hashes": {
            "base_campaign_manifest": base_manifest.content_hash,
            "receipt_campaign_manifest": receipt_manifest.content_hash,
            "feature_contract": contract.content_hash,
            "feature_seal": feature_seal.content_hash,
            "feature_seal_artifact": seal_reference.content_hash,
            "dataset": dataset.content_hash,
            "selection_partition_digest": selection.selection_partition_digest,
            "split_manifest": dataset.split_manifest_hash,
            "example_manifest": dataset.example_manifest_hash,
        },
        "members": {
            "observations": len(observations),
            "distinct_feature_record_hashes": len(set(feature_hashes.values())),
            "distinct_member_content_hashes": len(set(member_hashes.values())),
            "member_digest": _digest("\n".join(sorted(member_hashes.values()))),
        },
        "events": {
            "outcome_events": len(outcome_event_ids),
            "sequence_receipts": len(sequence_event_ids),
            "campaign_stream_version": await event_store.get_stream_version(campaign_id),
        },
        "artifact_lineage": {
            "feature_seal": seal_lineage.model_dump(mode="json"),
            "split_manifest": split_lineage.model_dump(mode="json"),
            "example_manifest": example_lineage.model_dump(mode="json"),
        },
        "restart": {
            "feature_seal_hash_reproduced": replayed_seal.content_hash == feature_seal.content_hash,
            "dataset_record_reproduced": restarted_dataset == dataset,
            "split_manifest_reproduced": restarted_dataset.split_manifest_hash
            == dataset.split_manifest_hash,
            "example_manifest_reproduced": restarted_dataset.example_manifest_hash
            == dataset.example_manifest_hash,
            "receipt_effective_remainder": len(resumed.effective_remainder),
            "receipt_members_match_dataset_members": True,
        },
    }


async def _run(output: Path) -> None:
    code_revision = _implementation_digest()
    with tempfile.TemporaryDirectory(prefix="cogos-d4-w1-artifacts-") as directory:
        authority = _ArtifactAuthority(Path(directory))
        partitions = [
            await _run_partition(
                partition=partition,
                corpus_role=corpus_role,
                groups=groups,
                authority=authority,
                code_revision=code_revision,
            )
            for partition, corpus_role, groups in PARTITIONS
        ]
        every_byte_verified = all(
            [
                await authority.verify(reference.artifact_id)
                for reference in authority.references.values()
            ]
        )

    identities = {item["hashes"]["dataset"] for item in partitions}
    if len(identities) != len(partitions):
        raise RuntimeError("two partitions produced one dataset identity")

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D4",
            "wave": "W1",
            "items": ["S21D4-023"],
            "recorded_at": RECORDED_AT,
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "fixture": (
                "two-partition v2 feature seal, explicit dataset, receipt-bound execution and "
                "restart, at Sprint 21D4's campaign sizes"
            ),
            "shape": {
                "partitions": len(partitions),
                "groups": sum(item["groups"] for item in partitions),
                "candidate_outcomes": sum(item["candidate_outcomes"] for item in partitions),
                "artifacts_stored": len(authority.references),
                "code_revision": code_revision,
            },
            "partitions": partitions,
            "artifact_bytes": {
                "every_stored_blob_rehashed": every_byte_verified,
                "blobs": len(authority.references),
            },
            "role_boundary": {
                "every_group_is_a_fixture_group": True,
                "d4_fitting_groups_used": 0,
                "d4_calibration_groups_used": 0,
                "d4_final_or_canary_groups_used": 0,
                "why": (
                    "a spine proof that borrowed a real group would spend it; the identifiers "
                    "name the fixture so an auditor does not have to trust the claim"
                ),
            },
            "migration_required": False,
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
                "partitions": [item["partition"] for item in partitions],
                "groups": evidence["shape"]["groups"],
                "candidate_outcomes": evidence["shape"]["candidate_outcomes"],
                "distinct_fitted_vectors": sum(
                    item["members"]["distinct_feature_record_hashes"] for item in partitions
                ),
                "effective_remainder": sum(
                    item["restart"]["receipt_effective_remainder"] for item in partitions
                ),
                "every_stored_blob_rehashed": every_byte_verified,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-seal-resume.json")
    arguments = parser.parse_args()
    asyncio.run(_run(arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
