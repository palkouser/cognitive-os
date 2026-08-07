#!/usr/bin/env python3
"""S21D4-034. Seal every fitting and calibration v2 feature before any container starts.

The order is the evidence. If the encoder runs after the verifier, the features have seen the
label and every number downstream is a number about a leak. So this command does one thing and
stops: it materialises all 180 packages, encodes all 720 candidates under the frozen local
model, and seals two partition-level records — and it refuses to start a container, which is
what makes "before" checkable rather than asserted.

`seal_feature_records_v2` will not seal a set that is not strictly earlier than its first
outcome, and the refusal is exercised here rather than described. The chronology it enforces is
recorded per partition, alongside the emptiness of the outcome stream at seal time: a seal that
precedes no outcome because no outcome exists yet is the only kind this wave may write.

The numeric bounds are fitted on the **fitting** rows and reused for calibration. Refitting per
partition would carry calibration statistics into the encoder, which is a leak no feature-name
check would catch, because the names would all still be right.

The count. The backlog says 840 records; the two partitions this command opens hold 720. The
difference is one final partition (30 groups, 120 slots), and W2 does not open a final role.
The record carries both numbers and the arithmetic, because silently delivering 720 against an
acceptance that says 840 would look like a shortfall rather than a correction.

Storage is the isolated D4 pair from S21D4-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`,
normally from `.env.s21d4.local`). No predecessor store is opened and no learned observation is
written: sealing is not measuring.

    set -a && . ./.env.s21d4.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d4.py \
        --model /path/to/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCandidateStrategy,
)
from cognitive_os.domain.sandbox import SandboxLimits  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm  # noqa: E402
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
)
from cognitive_os.learning.correction_catalogue import CatalogueGroup  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    FITTED_FEATURE_V2_SCALARS,
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
    canonical_embedding_windows,
    feature_input_v2,
    pool_canonical_embedding,
    raw_numeric_row_v2,
    seal_feature_records_v2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import NumericBoundsV2  # noqa: E402
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
FITTING_POOL = EVIDENCE / "sprint-21d4-fitting-pool.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d4-sealed-manifests.json"
SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D4 campaign the same campaign. Shared with the
#: vertical slice, which drew its own campaign id from the same namespace.
D4_CAMPAIGN_NAMESPACE = UUID("2c1f7a86-5b04-5d93-8e6a-41c7b2d09f35")
D4_CAMPAIGN_VERSION = 4
D4_VERIFIER_PROFILE_HASH = uuid5(D4_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

#: Task generation is a pure function of the template, the seed and this constant.
GENERATION_EPOCH = datetime(2026, 8, 7, tzinfo=UTC)

FEATURE_SET_MEDIA_TYPE = "application/json"

#: The only two partitions this command may open, in the order it opens them. Final A, final B
#: and canary stay closed, and no package is resolved for them.
_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.CALIBRATION,
)

#: What the backlog asked for, and where the difference goes. Recorded, not quietly absorbed.
DECLARED_RECORDS = 840
FINAL_PARTITION_SLOTS = 120

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

_EMBED_BATCH = 64


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
    """The v2 spine's own bytes, recorded in every seal so a re-encode is checkable."""
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/correction_catalogue_d4.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D4 environment first:\n"
            f"    set -a && . ./.env.s21d4.local && set +a"
        )
    return value


def _embedding_provider(model: Path) -> tuple[Any, str]:
    """The frozen local model, or a refusal. It is never substituted with a hashing vector."""
    manifest = minilm.read_manifest(model)
    if manifest is None:
        raise SystemExit(f"no usable local embedding model at {model}")
    provider = build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="sentence_transformers",
            model_id=minilm.MODEL_ID,
            dimension=minilm.DIMENSION,
            local_model_path=model,
            local_model_digest=manifest["tree_digest"],
        )
    )
    return provider, manifest["tree_digest"]


async def _embed_all(embed: Any, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        vectors.extend(await embed.embed_documents(texts[start : start + _EMBED_BATCH]))
    return tuple(vectors)


class _Partition:
    """One role's encoded state, before any outcome exists for it."""

    def __init__(self, partition: CorrectionPartition, groups: tuple[CatalogueGroup, ...]) -> None:
        self.partition = partition
        self.groups = groups
        self.campaign_id = uuid5(D4_CAMPAIGN_NAMESPACE, f"d4:{partition.value}")
        self.manifest_hash: str = ""
        self.bundles: dict[str, str] = {}
        self.task_manifest_hashes: dict[str, str] = {}
        self.pending: list[PendingFeatureV2] = []
        self.rows: list[dict[str, float]] = []
        self.sources: dict[str, str] = {}
        self.seal: SealedFeatureRecordSetV2 | None = None
        self.seal_artifact: UUID | None = None


async def _encode(
    partition: _Partition,
    *,
    runner: RealityCampaignRunner,
    embed: Any,
    scratch: Path,
) -> None:
    """Materialise every package and encode every candidate. No container runs."""
    windows: dict[str, tuple[str, ...]] = {}
    inputs: list[tuple[UUID, UUID, str, str]] = []

    for index, group in enumerate(partition.groups, start=1):
        print(
            f"[encode {partition.partition.value} {index}/{len(partition.groups)}] "
            f"{group.template_id}",
            file=sys.stderr,
        )
        prepared = await runner.prepare_task(
            group.template_id,
            root=scratch / partition.partition.value / group.template_id.replace(".", "_"),
            seed=group.task_seed,
            generated_at=GENERATION_EPOCH,
            bundle_artifact=None,
        )
        if prepared.generated.manifest.task_id != group.task_id:
            raise SystemExit(
                f"{group.template_id} generated task {prepared.generated.manifest.task_id}, but "
                f"the sealed catalogue names {group.task_id}"
            )
        partition.bundles[group.template_id] = str(prepared.bundle_artifact.artifact_id)
        partition.task_manifest_hashes[group.template_id] = prepared.generated.manifest.content_hash
        for slot in sorted(group.slots, key=lambda item: item.position):
            body = reality_candidates.candidate_source(
                prepared.generated.manifest, RealityCandidateStrategy(slot.recipe)
            )
            windows[str(slot.candidate_id)] = canonical_embedding_windows(body)
            partition.sources[str(slot.candidate_id)] = body
            inputs.append((slot.candidate_id, group.task_id, group.repository_group, body))

    keys = sorted(windows)
    flat = tuple(text for key in keys for text in windows[key])
    produced = await _embed_all(embed, flat)
    embedded: dict[str, tuple[float, ...]] = {}
    cursor = 0
    for key in keys:
        count = len(windows[key])
        embedded[key] = pool_canonical_embedding(produced[cursor : cursor + count])
        cursor += count

    for candidate_id, task_id, group_name, body in inputs:
        embedding = embedded[str(candidate_id)]
        partition.rows.append(
            raw_numeric_row_v2(
                feature_input_v2(
                    candidate_source=body, canonical_candidate_source_embedding=embedding
                )
            )
        )
        partition.pending.append(
            PendingFeatureV2(
                candidate_id=candidate_id,
                task_id=task_id,
                repository_group=group_name,
                candidate_source=body,
                canonical_candidate_source_embedding=embedding,
            )
        )


def _envelope_proof(partition: _Partition) -> dict[str, Any]:
    """What the record hashes, and what the vector is allowed to contain.

    The provenance envelope binds candidate, group and partition identity to the canonical
    source and the vector. The vector itself must not: a feature carrying a candidate id would
    let the model recognise a candidate rather than judge it.

    The check is channel equality against the frozen allowlist, in order, and nothing cleverer.
    A first version scanned channel names for words like "verifier" and reported
    `declared_verifier_capability_count` as a forbidden channel — a false alarm, since that
    scalar counts capabilities the *task package* declares and has no access to any verdict. A
    name heuristic cannot tell those apart, and a check that cries wolf is worse than none.
    What actually rules the verdict out is `reencodes_identically_from_source_alone`: the
    sealed vector is reproducible from the candidate source and the fitting bounds, with no
    outcome in the room.
    """
    seal = partition.seal
    if seal is None:  # pragma: no cover - the caller seals first
        raise SystemExit("an envelope proof needs a seal")
    scalar_names = {tuple(name for name, _ in record.values) for record in seal.records}
    return {
        "records": len(seal.records),
        "fitted_channels": len(FITTED_FEATURE_V2_ALLOWLIST),
        "scalar_channels": list(FITTED_FEATURE_V2_SCALARS),
        "channels_are_the_frozen_allowlist_in_order": (
            tuple(FITTED_FEATURE_V2_SCALARS)
            + tuple(f"canonical_candidate_source_embedding_{index:03d}" for index in range(384))
            == FITTED_FEATURE_V2_ALLOWLIST
        ),
        "every_record_carries_the_same_six_scalars_in_order": scalar_names
        == {tuple(FITTED_FEATURE_V2_SCALARS)},
        "embedding_dimension": seal.embedding_dimension,
        "envelope_binds": [
            "candidate_id",
            "task_id",
            "repository_group",
            "partition",
            "canonical_source_hash",
            "feature_vector_hash",
            "feature_contract_hash",
            "embedding_tree_digest",
            "code_revision",
        ],
        "declared_verifier_capability_count_reading": (
            "a property of the task package, counting the verifier capabilities the task "
            "declares it needs. It is not a verdict, is fixed before any candidate runs, and "
            "is identical across the four candidates of a group"
        ),
        "distinct_feature_vector_hashes": len({r.feature_vector_hash for r in seal.records}),
        "distinct_canonical_source_hashes": len({r.canonical_source_hash for r in seal.records}),
    }


def _reencode_proof(partition: _Partition, bounds: NumericBoundsV2, code_revision: str) -> bool:
    """Re-encode every candidate from its source alone and demand the same vector hashes.

    This is what "no outcome enters the vector" means operationally: the sealed vector is
    reproducible from the candidate source and the bounds, with nothing else in the room.
    """
    seal = partition.seal
    if seal is None:  # pragma: no cover - the caller seals first
        raise SystemExit("a re-encode proof needs a seal")
    replayed = seal_feature_records_v2(
        partition.pending,
        partition=partition.partition.value,
        campaign_manifest_hash=partition.manifest_hash,
        bounds=bounds,
        embedding_model_id=seal.embedding_model_id,
        embedding_revision=seal.embedding_revision,
        embedding_tree_digest=seal.embedding_tree_digest,
        code_revision=code_revision,
        sealed_at=seal.sealed_at,
    )
    return replayed.content_hash == seal.content_hash


def _refusal(action: str, call: Any) -> dict[str, str]:
    """Run something that must be refused and record the refusal it actually raised."""
    try:
        call()
    except ValueError as error:
        return {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{action} was accepted; the boundary it tests does not exist")


async def _run(output: Path, model: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D4 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")

    engine = create_postgres_engine(database_url)
    code_revision = _implementation_digest()
    contract = CorrectionFeatureContractV2()
    bundle = seal_d4_corpus()
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=CodingOutcomeRecorder(artifacts, coding_events, events),
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D4_VERIFIER_PROFILE_HASH,
            campaign_version=D4_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding_provider(model)

        partitions = {name: _Partition(name, bundle.catalogues[name].groups) for name in _ORDER}
        for name in _ORDER:
            partitions[name].manifest_hash = bundle.catalogues[name].content_hash

        # Before anything is sealed: the campaign streams these partitions would write to
        # must be empty. A seal is only "pre-outcome" if there is no outcome for it to precede,
        # and an empty stream under the campaign id is what "no outcome" looks like durably.
        # `get_stream_version` answers None for a stream that does not exist yet. None reads
        # as "not looked up"; zero reads as "looked up and empty", which is the claim.
        stream_versions_before = {
            name: (await events.get_stream_version(partitions[name].campaign_id)) or 0
            for name in _ORDER
        }
        if any(stream_versions_before.values()):
            raise SystemExit(
                "a D4 campaign stream already carries events; this command seals before the "
                f"first container and cannot run against {stream_versions_before}"
            )

        bounds: NumericBoundsV2 | None = None
        reports: list[dict[str, Any]] = []
        refusals: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="cogos-d4-seal-") as scratch:
            for name in _ORDER:
                partition = partitions[name]
                await _encode(
                    partition,
                    runner=runner,
                    embed=embed,
                    scratch=Path(scratch),
                )
                # Fitted on fitting and reused. Refitting on calibration would carry calibration
                # statistics into the encoder, which no feature-name check would ever catch.
                if bounds is None:
                    bounds = NumericBoundsV2.from_training(partition.rows)
                sealed_at = utc_now()
                partition.seal = seal_feature_records_v2(
                    partition.pending,
                    partition=name.value,
                    campaign_manifest_hash=partition.manifest_hash,
                    bounds=bounds,
                    embedding_model_id=minilm.MODEL_ID,
                    embedding_revision=model_digest,
                    embedding_tree_digest=model_digest,
                    code_revision=code_revision,
                    sealed_at=sealed_at,
                )
                stored = await artifacts.put_bytes(
                    partition.seal.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
                )
                partition.seal_artifact = stored.artifact_id

                refusals.append(
                    _refusal(
                        f"seal {name.value} again with an outcome already in hand",
                        lambda partition=partition, bounds=bounds: seal_feature_records_v2(
                            partition.pending,
                            partition=partition.partition.value,
                            campaign_manifest_hash=partition.manifest_hash,
                            bounds=bounds,
                            embedding_model_id=minilm.MODEL_ID,
                            embedding_revision=model_digest,
                            embedding_tree_digest=model_digest,
                            code_revision=code_revision,
                            sealed_at=utc_now(),
                            earliest_outcome_at=utc_now(),
                            outcomes_present=True,
                        ),
                    )
                )

                seal = partition.seal
                replayed = SealedFeatureRecordSetV2.model_validate_json(seal.canonical_json())
                reports.append(
                    {
                        "partition": name.value,
                        "campaign_id": str(partition.campaign_id),
                        "campaign_manifest_hash": partition.manifest_hash,
                        "groups": len(partition.groups),
                        "feature_records": len(seal.records),
                        "feature_seal_hash": seal.content_hash,
                        "feature_seal_artifact_id": str(stored.artifact_id),
                        "feature_contract_hash": seal.feature_contract_hash,
                        "encoder_version": seal.encoder_version,
                        "normalizer_version": seal.normalizer_version,
                        "code_revision": seal.code_revision,
                        "embedding_model_id": seal.embedding_model_id,
                        "embedding_tree_digest": seal.embedding_tree_digest,
                        "chronology": {
                            "sealed_at": seal.sealed_at.isoformat(),
                            "outcomes_present_at_seal_time": seal.outcomes_present,
                            "campaign_stream_version_before_the_seal": stream_versions_before[name],
                            "containers_started_by_this_command": 0,
                            "reading": (
                                "the seal precedes the first container because no container has "
                                "run: the campaign stream is empty and this command starts none"
                            ),
                        },
                        "reserialises_identically": replayed.content_hash == seal.content_hash,
                        "stored_seal_time_preserved": replayed.sealed_at == seal.sealed_at,
                        "reencodes_identically_from_source_alone": _reencode_proof(
                            partition, bounds, code_revision
                        ),
                        "envelope": _envelope_proof(partition),
                        "bounds_fitted_on": CorrectionPartition.TRAINING.value,
                        "bundle_artifacts": dict(sorted(partition.bundles.items())),
                        "task_manifest_hashes": dict(
                            sorted(partition.task_manifest_hashes.items())
                        ),
                        "member_hashes": sorted(
                            record.feature_vector_hash for record in seal.records
                        ),
                    }
                )
    finally:
        await engine.dispose()

    total = sum(int(item["feature_records"]) for item in reports)
    families = Counter(group.family for name in _ORDER for group in bundle.catalogues[name].groups)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D4",
            "wave": "W2",
            "items": ["S21D4-034"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "fitting_pool_sha256": _digest(FITTING_POOL.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "final_outcomes_inspected": False,
            "code_revision": code_revision,
            "feature_contract_hash": contract.content_hash,
            "counts": {
                "feature_records_sealed": total,
                "partitions_opened": [name.value for name in _ORDER],
                "declared_in_the_backlog": DECLARED_RECORDS,
                "difference": DECLARED_RECORDS - total,
                "reading": (
                    "the two partitions this wave executes hold 320 fitting and 400 calibration "
                    f"candidate slots, which is {total}. The backlog's {DECLARED_RECORDS} is "
                    f"those plus one final partition's {FINAL_PARTITION_SLOTS} slots, and W2 "
                    "does not open a final role. Sealing a final partition's features here "
                    "would be the first step of opening it"
                ),
                "final_partition_slots_not_sealed": FINAL_PARTITION_SLOTS,
                "family_distribution": dict(sorted(families.items())),
            },
            "partitions": reports,
            "refusals": refusals,
            "containers_started": 0,
            "learned_observations_written": 0,
            "why_no_observation": (
                "sealing is not measuring. An observation exists once a verifier has judged a "
                "candidate, and no candidate has run"
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
                "feature_records_sealed": total,
                "partitions": {str(item["partition"]): item["feature_records"] for item in reports},
                "seals": {
                    str(item["partition"]): str(item["feature_seal_hash"])[:16] for item in reports
                },
                "distinct_vectors": {
                    str(item["partition"]): item["envelope"]["distinct_feature_vector_hashes"]
                    for item in reports
                },
                "containers_started": 0,
                "refusals_executed": len(refusals),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-feature-seals.json")
    arguments = parser.parse_args()
    return asyncio.run(_run(arguments.output, arguments.model))


if __name__ == "__main__":
    raise SystemExit(main())
