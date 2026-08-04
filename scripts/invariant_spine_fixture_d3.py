#!/usr/bin/env python3
"""Run the Sprint 21D3 W1 v2 seal, dataset, receipt, and restart fixture."""

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
from cognitive_os.learning.correction_protocol import CorrectionFeatureContractV2  # noqa: E402
from cognitive_os.learning.correction_ranking import NumericBoundsV2  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"
SURFACE = "experience.correction_ranking"
TASK_ID = UUID("322438c3-8d9d-5adb-aa91-b3b6e3b898bb")
CAMPAIGN_ID = UUID("9906b6df-8e9f-593e-9e9b-3c48ad63be32")
SEALED_AT = datetime(2026, 8, 4, 9, tzinfo=UTC)
OUTCOME_AT = SEALED_AT + timedelta(hours=1)
RECORDED_AT = datetime.now(UTC).isoformat().replace("+00:00", "Z")
STRATEGIES = (
    RealityCandidateStrategy.RECIPE_ALPHA,
    RealityCandidateStrategy.RECIPE_BETA,
    RealityCandidateStrategy.RECIPE_GAMMA,
    RealityCandidateStrategy.RECIPE_DELTA,
)
SOURCES = (
    "def clamp(value):\n    return max(0, min(10, value))\n",
    "def clamp(value):\n    return 0 if value < 0 else min(10, value)\n",
    "def clamp(value):\n    return min(10, max(value, 0))\n",
    "def clamp(value):\n    if value < 0:\n        return 0\n    return min(value, 10)\n",
)
IMPLEMENTATION_FILES = (
    REPOSITORY / "src/cognitive_os/learning/correction_source.py",
    REPOSITORY / "src/cognitive_os/learning/correction_features.py",
    REPOSITORY / "src/cognitive_os/learning/correction_ranking.py",
)


def _digest(value: bytes | str) -> str:
    data = value.encode() if isinstance(value, str) else value
    return sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


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
        artifact_id = uuid5(NAMESPACE_URL, f"cogos:d3-w1-artifact:{blob.content_hash}")
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


def _embedding(seed: int) -> tuple[float, ...]:
    return tuple(((index + seed) % 19 - 9) / 10 for index in range(384))


async def _run(output: Path) -> None:
    code_revision = _implementation_digest()
    contract = CorrectionFeatureContractV2()
    candidates = tuple(uuid5(NAMESPACE_URL, f"cogos:d3-w1:candidate:{index}") for index in range(4))
    verifier_hash = _digest("d3-w1-verifier")
    task_manifest_hash = _digest("d3-w1-task")
    planned = tuple(
        RealityRunIdentity(
            task_id=TASK_ID,
            task_manifest_hash=task_manifest_hash,
            run_kind=RealityRunKind.CANDIDATE,
            candidate_id=candidate_id,
            strategy=strategy,
            source=RealityCandidateSource.CURATED,
            generator_profile_id="d3-w1-fixture",
            verifier_profile_hash=verifier_hash,
            campaign_version=3,
        )
        for candidate_id, strategy in zip(candidates, STRATEGIES, strict=True)
    )
    base_manifest = RealityCampaignManifest(
        campaign_id=CAMPAIGN_ID,
        campaign_version=3,
        planned_runs=planned,
        verifier_profile_hash=verifier_hash,
        created_at=SEALED_AT - timedelta(minutes=5),
    )
    raw = [
        raw_numeric_row_v2(
            feature_input_v2(
                candidate_source=source,
                canonical_candidate_source_embedding=_embedding(index),
            )
        )
        for index, source in enumerate(SOURCES)
    ]
    bounds = NumericBoundsV2.from_training(raw)
    pending = [
        PendingFeatureV2(
            candidate_id=candidate_id,
            task_id=TASK_ID,
            repository_group="d3-w1-fixture-group",
            candidate_source=source,
            canonical_candidate_source_embedding=_embedding(index),
        )
        for index, (candidate_id, source) in enumerate(zip(candidates, SOURCES, strict=True))
    ]
    feature_seal = seal_feature_records_v2(
        pending,
        partition="training",
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
        raise RuntimeError("serialized v2 feature seal did not reproduce")
    try:
        seal_feature_records_v2(
            pending,
            partition="training",
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
        raise RuntimeError("a post-outcome v2 feature seal was accepted")

    with tempfile.TemporaryDirectory(prefix="cogos-d3-w1-artifacts-") as directory:
        authority = _ArtifactAuthority(Path(directory))
        artifacts = LearnedArtifactStore(authority)  # type: ignore[arg-type]
        repository = InMemoryLearnedEvidenceRepository()
        seal_reference = await artifacts.store(
            feature_seal.canonical_json().encode(), media_type="application/json"
        )
        seal_lineage_id = uuid5(NAMESPACE_URL, "cogos:d3-w1:seal-lineage")
        seal_lineage = await artifacts.build_lineage(
            lineage_id=seal_lineage_id,
            artifact_id=seal_reference.artifact_id,
            role=LearnedArtifactRole.REPORT,
            declared_format="json",
            component_id="learned.knn.correction_ranking",
            producing_evidence_hash=feature_seal.content_hash,
            verified_by="s21d3-w1-fixture",
        )
        await repository.record_artifact_lineage(seal_lineage)

        observations: list[LearnedObservationRecord] = []
        outcome_references: list[ArtifactRef] = []
        hidden_references: list[ArtifactRef] = []
        for index, candidate_id in enumerate(candidates):
            outcome = await artifacts.store(
                f"candidate={candidate_id};accepted=false\n".encode(),
                media_type="application/json",
            )
            hidden = await artifacts.store(
                f"candidate={candidate_id};hidden=false\n".encode(),
                media_type="application/json",
            )
            outcome_references.append(outcome)
            hidden_references.append(hidden)
            observation = LearnedObservationRecord(
                observation_id=uuid5(NAMESPACE_URL, f"cogos:d3-w1:observation:{index}"),
                surface=SURFACE,
                source_kind="self_play_task_run",
                source_task_id=TASK_ID,
                source_payload_hash=outcome.content_hash,
                provenance_class=ProvenanceClass.SELF_PLAY,
                attribution=ObservationAttribution.DIRECT,
                status=ObservationStatus.ACCEPTED,
                verifier_status="failed",
                verifier_evidence_hash=hidden.content_hash,
                usage_rights_verified=True,
                sensitivity="internal",
                decision_reason="deterministic W1 feature-seal and resume fixture",
                evaluation_eligible=True,
                idempotency_key=f"s21d3-w1-observation-{index}",
                recorded_at=OUTCOME_AT + timedelta(seconds=index),
            )
            observations.append(await repository.record_observation(observation))

        feature_hashes = {
            str(observation.observation_id): feature_seal.record_for(candidate_id).content_hash
            for observation, candidate_id in zip(observations, candidates, strict=True)
        }
        outcome_hashes = {
            str(observation.observation_id): reference.content_hash
            for observation, reference in zip(observations, outcome_references, strict=True)
        }
        member_hashes = {
            identity: _digest(f"{identity}:{feature_hashes[identity]}:{outcome_hashes[identity]}")
            for identity in feature_hashes
        }
        observation_ids = tuple(str(item.observation_id) for item in observations)
        selection = ExplicitSelection(
            partition="training",
            members=tuple(
                (str(item.observation_id), item.source_payload_hash) for item in observations
            ),
            groups={item: "d3-w1-fixture-group" for item in observation_ids},
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
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=contract.content_hash,
            revision=3,
            selection=selection,
        )

        receipt_manifest = RealityCampaignReceiptManifestV3(
            **base_manifest.model_dump(exclude={"content_hash"}),
            partition="training",
            mode="label_all",
            selection_manifest_hash=dataset.split_manifest_hash,
            feature_schema_hash=contract.content_hash,
            feature_seal_root_hash=feature_seal.content_hash,
            receipt_tasks=(
                RealityReceiptTaskV3(
                    task_id=TASK_ID,
                    task_manifest_hash=task_manifest_hash,
                    bundle_id=uuid5(NAMESPACE_URL, "cogos:d3-w1:bundle"),
                    bundle_hash=_digest("d3-w1-bundle"),
                    feature_seal_hash=feature_seal.content_hash,
                    candidate_order=candidates,
                    selected_member_hashes=tuple(member_hashes[item] for item in observation_ids),
                ),
            ),
        )
        event_store = MemoryEventStore()
        events = CodingEventService(event_store)
        task_run_ids: list[UUID] = []
        outcome_event_ids: list[UUID] = []
        for index, identity in enumerate(planned):
            task_run_id = uuid5(NAMESPACE_URL, f"cogos:d3-w1:task-run:{index}")
            task_run_ids.append(task_run_id)
            outcome_event_ids.append(
                await events.append(
                    task_run_id,
                    CodingOutcomeRecorded(
                        task_run_id=task_run_id,
                        run_kind=RealityRunKind.CANDIDATE,
                        task_id=TASK_ID,
                        task_manifest_hash=task_manifest_hash,
                        candidate_id=identity.candidate_id,
                        candidate_strategy=identity.strategy,
                        outcome_hash=outcome_references[index].content_hash,
                        outcome_artifact_id=outcome_references[index].artifact_id,
                        outcome_artifact_hash=outcome_references[index].content_hash,
                        hidden_evidence_artifact_id=hidden_references[index].artifact_id,
                        hidden_evidence_hash=hidden_references[index].content_hash,
                        final_status="failed",
                        hidden_verification_passed=False,
                        run_identity_key=identity.key,
                        occurred_at=OUTCOME_AT + timedelta(seconds=index),
                    ),
                    correlation_id=CAMPAIGN_ID,
                    stream_type=StreamType.TASK_RUN,
                )
            )
        sequence_event_id = await events.append(
            CAMPAIGN_ID,
            RealityCampaignSequenceRecorded(
                campaign_id=CAMPAIGN_ID,
                task_id=TASK_ID,
                partition="training",
                mode="label_all",
                campaign_manifest_hash=receipt_manifest.content_hash,
                baseline_order=candidates,
                resolved_order=candidates,
                attempted_order=candidates,
                intentionally_unattempted=(),
                stop_reason="exhausted_without_acceptance",
                occurred_at=OUTCOME_AT + timedelta(minutes=1),
            ),
            correlation_id=CAMPAIGN_ID,
            stream_type=StreamType.SYSTEM,
        )

        # Restart means fresh application services over the same durable authorities.
        restarted_builder = LearnedDatasetBuilder(
            repository,
            LearnedArtifactStore(authority),
            clock=lambda: OUTCOME_AT + timedelta(days=1),  # type: ignore[arg-type]
        )
        restarted_dataset = await restarted_builder.build(
            surface=SURFACE,
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=contract.content_hash,
            revision=3,
            selection=selection,
        )
        resumed = await RealityCampaignLedger(event_store).plan_resume_with_receipts(
            receipt_manifest,
            task_run_ids=task_run_ids,
            campaign_id=CAMPAIGN_ID,
        )
        if restarted_dataset != dataset or resumed.effective_remainder:
            raise RuntimeError("restart did not reproduce dataset identity or completed receipt")
        # The receipt stores member hashes, not raw feature hashes; compare it explicitly to
        # the dataset selection so the two identities cannot be accidentally conflated.
        if tuple(member_hashes[item] for item in observation_ids) != (
            receipt_manifest.receipt_tasks[0].selected_member_hashes
        ):
            raise RuntimeError("receipt members no longer resolve the dataset selection")

        split_lineage_id = uuid5(
            DATASET_NAMESPACE, f"{dataset.dataset_id}|{LearnedArtifactRole.SPLIT_MANIFEST.value}"
        )
        example_lineage_id = uuid5(
            DATASET_NAMESPACE, f"{dataset.dataset_id}|{LearnedArtifactRole.EXAMPLE_MANIFEST.value}"
        )
        split_lineage = await repository.get_artifact_lineage(split_lineage_id)
        example_lineage = await repository.get_artifact_lineage(example_lineage_id)
        if split_lineage is None or example_lineage is None:
            raise RuntimeError("dataset manifest lineage did not survive restart")

        evidence = _seal(
            {
                "schema_version": 1,
                "sprint": "21D3",
                "wave": "W1",
                "items": ["S21D3-028"],
                "recorded_at": RECORDED_AT,
                "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
                "fixture": "seeded W4-F3 pre-outcome feature-seal and receipt restart regression",
                "chronology": {
                    "base_manifest_created_at": base_manifest.created_at.isoformat(),
                    "features_sealed_at": feature_seal.sealed_at.isoformat(),
                    "first_outcome_at": OUTCOME_AT.isoformat(),
                    "sequence_receipt_at": (OUTCOME_AT + timedelta(minutes=1)).isoformat(),
                    "strictly_pre_outcome": feature_seal.sealed_at < OUTCOME_AT,
                    "stored_seal_time_preserved": replayed_seal.sealed_at == feature_seal.sealed_at,
                    "post_outcome_seal_refusal": post_outcome_refusal,
                },
                "hashes": {
                    "base_campaign_manifest": base_manifest.content_hash,
                    "receipt_campaign_manifest": receipt_manifest.content_hash,
                    "feature_contract": contract.content_hash,
                    "implementation_tree": code_revision,
                    "feature_seal": feature_seal.content_hash,
                    "feature_seal_artifact": seal_reference.content_hash,
                    "dataset": dataset.content_hash,
                    "selection_partition_digest": selection.selection_partition_digest,
                    "split_manifest": dataset.split_manifest_hash,
                    "example_manifest": dataset.example_manifest_hash,
                },
                "members": [
                    {
                        "candidate_id": str(candidate_id),
                        "observation_id": str(observation.observation_id),
                        "feature_record_hash": feature_hashes[str(observation.observation_id)],
                        "outcome_hash": outcome_hashes[str(observation.observation_id)],
                        "member_content_hash": member_hashes[str(observation.observation_id)],
                    }
                    for candidate_id, observation in zip(candidates, observations, strict=True)
                ],
                "artifact_lineage": {
                    "feature_seal": seal_lineage.model_dump(mode="json"),
                    "split_manifest": split_lineage.model_dump(mode="json"),
                    "example_manifest": example_lineage.model_dump(mode="json"),
                    "all_bytes_verified": all(
                        [
                            await authority.verify(reference.artifact_id)
                            for reference in authority.references.values()
                        ]
                    ),
                },
                "events": {
                    "outcome_event_ids": [str(item) for item in outcome_event_ids],
                    "sequence_event_id": str(sequence_event_id),
                    "campaign_stream_version": await event_store.get_stream_version(CAMPAIGN_ID),
                },
                "restart": {
                    "feature_seal_hash_reproduced": replayed_seal.content_hash
                    == feature_seal.content_hash,
                    "dataset_record_reproduced": restarted_dataset == dataset,
                    "receipt_effective_remainder": [],
                    "receipt_members_match_dataset_members": True,
                },
                "migration_required": False,
            }
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=EVIDENCE / "sprint-21d3-v2-seal-resume.json",
    )
    arguments = parser.parse_args()
    asyncio.run(_run(arguments.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
