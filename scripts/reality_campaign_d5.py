#!/usr/bin/env python3
"""S21D5-025 and S21D5-026. Seal every feature before any container, then run both campaigns.

The order is the evidence. If the encoder runs after the verifier, the features have seen the
label and every number downstream is a number about a leak. So this command does one thing and
stops: it materialises all 280 packages, encodes all 1,120 candidates under the frozen local
model, and seals two partition-level records — and it refuses to start a container, which is
what makes "before" checkable rather than asserted.

`seal_feature_records_v2` will not seal a set that is not strictly earlier than its first
outcome, and the refusal is exercised here rather than described. The chronology it enforces is
recorded per partition, alongside the emptiness of the outcome stream at seal time: a seal that
precedes no outcome because no outcome exists yet is the only kind this wave may write.

The numeric bounds are fitted on the **fitting** rows and reused for calibration. Refitting per
partition would carry calibration statistics into the encoder, which is a leak no feature-name
check would catch, because the names would all still be right.

What is different from D4, and why it needs saying: 180 of the 280 packages are D4's own groups,
re-executed. They keep their bodies and take **D5 candidate identities**, because the catalogue
seed reaches candidate identity. That is the whole content of "re-executed under new run
identities", and it is checked rather than assumed — every generated task id must equal the one
the D5 sealed catalogue names, and no candidate identity may coincide with a D4 one.

Storage is the isolated D5 pair from S21D5-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`).
No predecessor store is opened and no learned observation is written: sealing is not measuring.

The execute stage is S21D5-026 and runs one partition at a time under `label_all`: 720 fitting
outcomes over 180 groups, then 400 calibration outcomes over 100. It reloads the seal out of the
artifact store rather than rebuilding it -- a campaign that re-derives its seal executes against
whatever the encoder produces today -- and refuses to start if any task manifest no longer hashes
to what the seal was bound to. After the runs it replays every identity off the durable receipt,
and a replay that starts a container is a resume that pays for its work twice.

    set -a && . ./.env.s21d5.local && set +a
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d5.py \
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d5.py \
        --stage execute --partition training
    UV_CACHE_DIR=.cache/uv uv run python scripts/reality_campaign_d5.py \
        --stage execute --partition calibration
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

from cognitive_os.application.services.correction_candidate_sequencer import (  # noqa: E402
    AttemptResult,
    CorrectionCandidateSequencer,
    SequenceMode,
)
from cognitive_os.application.services.correction_ranking_observations import (  # noqa: E402
    CorrectionRankingObservationProjector,
)
from cognitive_os.application.services.learned_evidence import (  # noqa: E402
    LearnedEvidenceService,
)
from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.coding.reality_tasks import GENERATOR_PROFILE_ID  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCampaignReceiptManifestV3,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityReceiptTaskV3,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.domain.sandbox import SandboxLimits  # noqa: E402
from cognitive_os.events.catalog import build_default_event_catalog  # noqa: E402
from cognitive_os.events.coding_event_service import CodingEventService  # noqa: E402
from cognitive_os.events.learned_event_service import LearnedEventService  # noqa: E402
from cognitive_os.infrastructure.artifacts.filesystem import (  # noqa: E402
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService  # noqa: E402
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm  # noqa: E402
from cognitive_os.infrastructure.learned.postgres.repository import (  # noqa: E402
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
)
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CatalogueGroup,
    campaign_manifest_from_groups,
)
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d5 import seal_d5_corpus  # noqa: E402
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
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d5-sealed-manifests.json"
SEPARATION = EVIDENCE / "sprint-21d5-corpus-separation.json"
SEAL_RECORD = EVIDENCE / "sprint-21d5-feature-seals.json"
SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D5 campaign the same campaign.
D5_CAMPAIGN_NAMESPACE = UUID("8ce6e0b5-5fb1-5547-abc2-5113999efda8")
D5_CAMPAIGN_VERSION = 5
D5_VERIFIER_PROFILE_HASH = uuid5(D5_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

#: Task generation is a pure function of the template, the seed and this constant.
GENERATION_EPOCH = datetime(2026, 8, 8, tzinfo=UTC)

FEATURE_SET_MEDIA_TYPE = "application/json"

#: S21D5-026 names one item for both partitions, and each run writes its own record, or the
#: second would overwrite the first campaign's.
CAMPAIGN_RECORD = {
    CorrectionPartition.TRAINING: EVIDENCE / "sprint-21d5-self-play-campaign.json",
    CorrectionPartition.CALIBRATION: EVIDENCE / "sprint-21d5-calibration-campaign.json",
}

ACTOR = "reality-campaign-d5"
AUTHORITY = "S21D5-026"

#: The only two partitions this command may open, in the order it opens them. Final A, final B
#: and canary stay closed, and no package is resolved for them.
_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.CALIBRATION,
)

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
    """The convention, unchanged since D4: the bytes hashed are the bytes written."""
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
        "src/cognitive_os/learning/correction_catalogue_d5.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D5 environment first:\n"
            f"    set -a && . ./.env.s21d5.local && set +a"
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
        self.campaign_id = uuid5(D5_CAMPAIGN_NAMESPACE, f"d5:{partition.value}")
        self.manifest_hash: str = ""
        self.bundles: dict[str, str] = {}
        self.task_manifest_hashes: dict[str, str] = {}
        self.pending: list[PendingFeatureV2] = []
        self.rows: list[dict[str, float]] = []
        self.sources: dict[str, str] = {}
        self.seal: SealedFeatureRecordSetV2 | None = None
        self.seal_artifact: UUID | None = None


async def _encode(
    partition: _Partition, *, runner: RealityCampaignRunner, embed: Any, scratch: Path
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
    D4 recorded why a name heuristic is worse than none, and that reading is unchanged: what
    rules a verdict out is `reencodes_identically_from_source_alone`, not a word search.
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


def _identity_proof(partitions: dict[CorrectionPartition, _Partition]) -> dict[str, Any]:
    """The 180 re-executed groups must carry D5 identities, not D4's.

    D5's fitting pool is D4's two partitions by *body*, and the contract calls for them to be
    re-executed under new run identities rather than read from a predecessor store. The seed
    reaches candidate identity, so this is checkable: not one of D5's candidate identities may
    equal a D4 one, and not one of D5's task identities may either. Asserting the seeds differ
    would only restate the input.
    """
    d4 = seal_d4_corpus()
    d4_candidates = {
        str(slot.candidate_id)
        for catalogue in d4.catalogues.values()
        for group in catalogue.groups
        for slot in group.slots
    }
    d4_tasks = {
        str(group.task_id) for catalogue in d4.catalogues.values() for group in catalogue.groups
    }
    d5_candidates = {
        str(slot.candidate_id)
        for partition in partitions.values()
        for group in partition.groups
        for slot in group.slots
    }
    d5_tasks = {
        str(group.task_id) for partition in partitions.values() for group in partition.groups
    }
    carried = {
        group.repository_group for partition in partitions.values() for group in partition.groups
    } & {
        group.repository_group for catalogue in d4.catalogues.values() for group in catalogue.groups
    }
    return {
        "groups_carried_by_body_from_d4": len(carried),
        "d5_candidate_identities": len(d5_candidates),
        "candidate_identities_shared_with_d4": sorted(d5_candidates & d4_candidates),
        "task_identities_shared_with_d4": sorted(d5_tasks & d4_tasks),
        "distinct": not (d5_candidates & d4_candidates) and not (d5_tasks & d4_tasks),
        "reading": (
            "the same 180 task packages under 720 identities that have never been run; a shared "
            "identity would let a D4 row be mistaken for a D5 one on resume"
        ),
    }


def _refusal(action: str, call: Any) -> dict[str, str]:
    """Run something that must be refused and record the refusal it actually raised."""
    try:
        call()
    except ValueError as error:
        return {"action": action, "refused": "true", "error": f"{type(error).__name__}: {error}"}
    raise SystemExit(f"{action} was accepted; the boundary it tests does not exist")


async def _stage_seal(output: Path, model: Path, limit: int | None) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3", "s21d4"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D5 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")

    engine = create_postgres_engine(database_url)
    code_revision = _implementation_digest()
    contract = CorrectionFeatureContractV2()
    bundle = seal_d5_corpus()
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
            verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
            campaign_version=D5_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding_provider(model)

        partitions = {
            name: _Partition(name, bundle.catalogues[name].groups[:limit]) for name in _ORDER
        }
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
                "a D5 campaign stream already carries events; this command seals before the "
                f"first container and cannot run against {stream_versions_before}"
            )

        bounds: NumericBoundsV2 | None = None
        reports: list[dict[str, Any]] = []
        refusals: list[dict[str, str]] = []
        with tempfile.TemporaryDirectory(prefix="cogos-d5-seal-") as scratch:
            for name in _ORDER:
                partition = partitions[name]
                await _encode(partition, runner=runner, embed=embed, scratch=Path(scratch))
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
    families = Counter(
        group.family for partition in partitions.values() for group in partition.groups
    )
    identity = _identity_proof(partitions)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W1",
            "items": ["S21D5-025"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "separation_sha256": _digest(SEPARATION.read_bytes()),
            "final_outcomes_inspected": False,
            "code_revision": code_revision,
            "feature_contract_hash": contract.content_hash,
            "corpus_seal_hash": bundle.seal.content_hash,
            "counts": {
                "feature_records_sealed": total,
                "partitions_opened": [name.value for name in _ORDER],
                "fitting_candidate_slots": len(partitions[CorrectionPartition.TRAINING].pending),
                "calibration_candidate_slots": len(
                    partitions[CorrectionPartition.CALIBRATION].pending
                ),
                "reading": (
                    "the two partitions this wave executes hold 720 fitting and 400 calibration "
                    f"candidate slots, which is {total}. No final or canary partition is opened; "
                    "sealing one's features here would be the first step of opening it"
                ),
                "final_and_canary_slots_not_sealed": 260,
                "family_distribution": dict(sorted(families.items())),
            },
            "run_identities": identity,
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
                "run_identities_distinct_from_d4": identity["distinct"],
                "containers_started": 0,
                "refusals_executed": len(refusals),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


# ------------------------------------------------------------------------------- S21D5-026


def _receipt_manifest(
    *,
    groups: tuple[CatalogueGroup, ...],
    partition: CorrectionPartition,
    campaign_id: UUID,
    seal: SealedFeatureRecordSetV2,
    manifest_hash: str,
    task_manifest_hashes: dict[str, str],
    bundles: dict[str, str],
) -> RealityCampaignReceiptManifestV3:
    """The durable receipt, bound at the seal's time rather than at execution's.

    `created_at` is the seal time on purpose: a receipt written when the containers start
    records what happened, and what this needs to record is what was planned before they did.
    """
    planned: list[RealityRunIdentity] = []
    for group in groups:
        manifest_hash_of_task = task_manifest_hashes[group.template_id]
        for slot in sorted(group.slots, key=lambda item: item.position):
            planned.append(
                RealityRunIdentity(
                    task_id=group.task_id,
                    task_manifest_hash=manifest_hash_of_task,
                    run_kind=RealityRunKind.CANDIDATE,
                    candidate_id=slot.candidate_id,
                    strategy=RealityCandidateStrategy(slot.recipe),
                    source=RealityCandidateSource.CURATED,
                    generator_profile_id=GENERATOR_PROFILE_ID,
                    verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
                    campaign_version=D5_CAMPAIGN_VERSION,
                )
            )
        planned.append(
            RealityRunIdentity(
                task_id=group.task_id,
                task_manifest_hash=manifest_hash_of_task,
                run_kind=RealityRunKind.BASELINE,
                source=RealityCandidateSource.BASELINE,
                generator_profile_id=GENERATOR_PROFILE_ID,
                verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
                campaign_version=D5_CAMPAIGN_VERSION,
            )
        )
    return RealityCampaignReceiptManifestV3(
        campaign_id=campaign_id,
        campaign_version=D5_CAMPAIGN_VERSION,
        planned_runs=tuple(planned),
        verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
        created_at=seal.sealed_at,
        partition=partition.value,
        mode="label_all",
        selection_manifest_hash=manifest_hash,
        feature_schema_hash=seal.feature_contract_hash,
        feature_seal_root_hash=seal.content_hash,
        receipt_tasks=tuple(
            RealityReceiptTaskV3(
                task_id=group.task_id,
                task_manifest_hash=task_manifest_hashes[group.template_id],
                bundle_id=UUID(bundles[group.template_id]),
                bundle_hash=_digest(bundles[group.template_id]),
                feature_seal_hash=seal.content_hash,
                candidate_order=tuple(
                    slot.candidate_id for slot in sorted(group.slots, key=lambda s: s.position)
                ),
                selected_member_hashes=tuple(
                    seal.record_for(slot.candidate_id).feature_vector_hash
                    for slot in sorted(group.slots, key=lambda s: s.position)
                ),
            )
            for group in groups
        ),
    )


async def _stage_execute(output: Path, partition: CorrectionPartition, limit: int | None) -> int:
    """Run one partition under `label_all`, project role-bound, then replay off the receipt."""
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2", "s21d3", "s21d4"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D5 writes only to its own pair")

    sealed = json.loads(SEAL_RECORD.read_text(encoding="utf-8"))
    row = next(item for item in sealed["partitions"] if item["partition"] == partition.value)
    catalogue = seal_d5_corpus().catalogues[partition]
    groups = catalogue.groups[: limit or len(catalogue.groups)]

    engine = create_postgres_engine(database_url)
    contract = CorrectionFeatureContractV2()
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))
        ledger = RealityCampaignLedger(events)
        sequencer = CorrectionCandidateSequencer(coding_events)
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=CodingOutcomeRecorder(artifacts, coding_events, events),
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D5_VERIFIER_PROFILE_HASH,
            campaign_version=D5_CAMPAIGN_VERSION,
        )

        # The seal comes back out of the artifact store rather than being rebuilt. A campaign
        # that re-derives its seal would execute against whatever the encoder produces today.
        seal_bytes = await artifacts.get_bytes(UUID(row["feature_seal_artifact_id"]))
        seal = SealedFeatureRecordSetV2.model_validate_json(seal_bytes.decode())
        if seal.content_hash != row["feature_seal_hash"]:
            raise SystemExit(
                f"the stored feature seal hashes to {seal.content_hash}, not the "
                f"{row['feature_seal_hash']} S21D5-025 recorded"
            )

        campaign_id = uuid5(D5_CAMPAIGN_NAMESPACE, f"d5:{partition.value}")
        prepared_of = {}
        with tempfile.TemporaryDirectory(prefix="cogos-d5-run-") as scratch:
            for index, group in enumerate(groups, start=1):
                print(
                    f"[prepare {partition.value} {index}/{len(groups)}] {group.template_id}",
                    file=sys.stderr,
                )
                prepared = await runner.prepare_task(
                    group.template_id,
                    root=Path(scratch) / group.template_id.replace(".", "_"),
                    seed=group.task_seed,
                    generated_at=GENERATION_EPOCH,
                    bundle_artifact=await artifacts.describe(
                        UUID(row["bundle_artifacts"][group.template_id])
                    ),
                )
                recorded_hash = row["task_manifest_hashes"][group.template_id]
                if prepared.generated.manifest.content_hash != recorded_hash:
                    raise SystemExit(
                        f"{group.template_id}: the task manifest hashes to "
                        f"{prepared.generated.manifest.content_hash}, not the {recorded_hash} the "
                        "seal was bound to; every planned run identity would differ"
                    )
                prepared_of[group.template_id] = prepared

            receipt = _receipt_manifest(
                groups=groups,
                partition=partition,
                campaign_id=campaign_id,
                seal=seal,
                manifest_hash=row["campaign_manifest_hash"],
                task_manifest_hashes=row["task_manifest_hashes"],
                bundles=row["bundle_artifacts"],
            )
            manifest = campaign_manifest_from_groups(
                groups,
                partition=partition,
                manifest_hash=row["campaign_manifest_hash"],
                campaign_id=campaign_id,
                campaign_version=D5_CAMPAIGN_VERSION,
                feature_sealed_at=seal.sealed_at,
            )
            projector = CorrectionRankingObservationProjector(manifest)

            runs: dict[UUID, Any] = {}
            baselines: list[Any] = []
            observations: list[dict[str, Any]] = []
            sequences: list[dict[str, Any]] = []

            def _attempt(prepared: Any, recipe_of: dict[UUID, RealityCandidateStrategy]) -> Any:
                async def attempt(candidate_id: UUID) -> AttemptResult:
                    run = await runner.run_candidate(
                        prepared, recipe_of[candidate_id], completed={}, candidate_id=candidate_id
                    )
                    runs[candidate_id] = run
                    reference = run.step.reference
                    return AttemptResult(
                        candidate_id=candidate_id,
                        accepted=reference.hidden_verification_passed,
                        event_id=reference.source_event_id,
                        verifier_evidence_hash=reference.hidden_evidence_hash,
                    )

                return attempt

            for index, group in enumerate(groups, start=1):
                print(
                    f"[run {partition.value} {index}/{len(groups)}] {group.template_id}",
                    file=sys.stderr,
                )
                prepared = prepared_of[group.template_id]
                ordered = sorted(group.slots, key=lambda item: item.position)
                recipe_of = {
                    slot.candidate_id: RealityCandidateStrategy(slot.recipe) for slot in ordered
                }
                baselines.append(await runner.run_baseline(prepared, completed={}))
                sequence = await sequencer.run_task(
                    campaign_id=campaign_id,
                    task_id=group.task_id,
                    partition=partition.value,
                    mode=SequenceMode.LABEL_ALL,
                    campaign_manifest_hash=receipt.content_hash,
                    baseline_order=tuple(slot.candidate_id for slot in ordered),
                    attempt=_attempt(prepared, recipe_of),
                )
                await sequencer.record(sequence, correlation_id=group.task_id)
                sequences.append(
                    {
                        "task_id": str(group.task_id),
                        "attempted": len(sequence.attempted_order),
                        "intentionally_unattempted": len(sequence.intentionally_unattempted),
                        "stop_reason": sequence.stop_reason,
                    }
                )
                for slot in ordered:
                    run = runs[slot.candidate_id]
                    stored = await learned.record_observation(
                        projector.project(
                            run.step.reference,
                            campaign_version=D5_CAMPAIGN_VERSION,
                            verifier_profile_hash=group.verifier_profile_hash,
                            usage_rights_verified=group.usage_rights_verified,
                        ),
                        correlation_id=run.step.reference.task_run_id,
                        actor=ACTOR,
                        authority=AUTHORITY,
                    )
                    observations.append(
                        {
                            "observation_id": str(stored.observation_id),
                            "candidate_id": str(slot.candidate_id),
                            "group": group.repository_group,
                            "task_id": str(group.task_id),
                            "accepted": run.step.reference.hidden_verification_passed,
                            "provenance_class": str(stored.provenance_class),
                            "verifier_status": stored.verifier_status,
                            "outcome_hash": run.step.reference.outcome_hash,
                            "payload_hash": stored.source_payload_hash,
                            "feature_vector_hash": seal.record_for(
                                slot.candidate_id
                            ).feature_vector_hash,
                        }
                    )

            # The replay. A second pass over the same identities that starts no container is
            # what "receipt-aware" means; asserting resumability without re-running proves the
            # ledger can be queried, not that the campaign can be resumed.
            references = [run.step.reference for run in runs.values()]
            task_run_ids = [item.task_run_id for item in references] + [
                run.step.reference.task_run_id for run in baselines
            ]
            recorded = dict(await ledger.completed_by_identity(task_run_ids))
            replayed: list[Any] = []
            for group in groups:
                prepared = prepared_of[group.template_id]
                replayed.append(await runner.run_baseline(prepared, completed=recorded))
                for slot in sorted(group.slots, key=lambda item: item.position):
                    replayed.append(
                        await runner.run_candidate(
                            prepared,
                            RealityCandidateStrategy(slot.recipe),
                            completed=recorded,
                            candidate_id=slot.candidate_id,
                        )
                    )
            resumed = await ledger.plan_resume_with_receipts(
                receipt, task_run_ids=task_run_ids, campaign_id=campaign_id
            )
    finally:
        await engine.dispose()

    count = count_outcomes(references)
    provenance = Counter(str(item["provenance_class"]) for item in observations)
    accepted_by_recipe: Counter[str] = Counter()
    by_recipe: Counter[str] = Counter()
    for reference in references:
        label = "" if reference.strategy is None else reference.strategy.value
        by_recipe[label] += 1
        if reference.hidden_verification_passed:
            accepted_by_recipe[label] += 1

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W1",
            "items": ["S21D5-026"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "feature_seals_sha256": _digest(SEAL_RECORD.read_bytes()),
            "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
            "final_outcomes_inspected": False,
            "partition": partition.value,
            "campaign_id": str(campaign_id),
            "campaign_manifest_hash": row["campaign_manifest_hash"],
            "receipt_manifest_hash": receipt.content_hash,
            "feature_seal_hash": seal.content_hash,
            "feature_seal_reloaded_from_the_artifact_store": True,
            "feature_contract_hash": contract.content_hash,
            "mode": "label_all",
            "execution": {
                "groups": len(groups),
                "candidate_runs": len(references),
                "baselines": len(baselines),
                "containers_started": len(references) + len(baselines),
                "unique_outcomes": count.unique,
                "duplicates_excluded": count.duplicates_excluded,
                "hidden_passed": count.passed,
                "hidden_failed": count.failed,
                "baselines_passing_hidden_verification": sum(
                    1 for run in baselines if run.hidden_passed
                ),
                "candidates_left_unattempted": sum(
                    int(item["intentionally_unattempted"]) for item in sequences
                ),
                "sequences_recorded": len(sequences),
                "stop_reasons": dict(Counter(str(item["stop_reason"]) for item in sequences)),
                "acceptance_by_recipe": {
                    name: round(accepted_by_recipe[name] / by_recipe[name], 4)
                    for name in sorted(by_recipe)
                },
                "every_outcome_follows_the_seal": all(
                    item.occurred_at > seal.sealed_at for item in references
                ),
            },
            "observations": {
                "recorded": len(observations),
                "provenance_counts": dict(sorted(provenance.items())),
                "real_governed_runs": provenance.get("ProvenanceClass.REAL_GOVERNED_RUN", 0)
                + provenance.get("real_governed_run", 0),
                "distinct_feature_vector_hashes": len(
                    {str(item["feature_vector_hash"]) for item in observations}
                ),
                "groups": len({str(item["group"]) for item in observations}),
            },
            "resume": {
                "run_identities_resolved_from_the_receipt": len(recorded),
                "runs_replayed": sum(1 for run in replayed if run.replayed),
                "containers_started_on_the_replay": sum(1 for run in replayed if not run.replayed),
                "receipt_is_resumable": resumed.is_resumable,
                "receipt_effective_remainder": [str(item) for item in resumed.effective_remainder],
            },
            "task_run_ids": sorted(str(item) for item in task_run_ids),
            "candidate_outcomes": observations,
            "sequences": sequences,
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
                "partition": partition.value,
                "groups": len(groups),
                "candidate_runs": len(references),
                "hidden_passed": count.passed,
                "baselines_passing_hidden": evidence["execution"][
                    "baselines_passing_hidden_verification"
                ],
                "real_governed_runs": evidence["observations"]["real_governed_runs"],
                "observations": len(observations),
                "containers_on_the_replay": evidence["resume"]["containers_started_on_the_replay"],
                "effective_remainder": len(evidence["resume"]["receipt_effective_remainder"]),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("seal", "execute"), default="seal")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--partition", choices=[name.value for name in _ORDER], default="training")
    parser.add_argument("--groups", type=int, default=None, help="smoke-test limit")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    if arguments.stage == "execute":
        partition = CorrectionPartition(arguments.partition)
        if arguments.groups is not None and arguments.output is None:
            raise SystemExit("--groups writes a partial record; give it an --output of its own")
        return asyncio.run(
            _stage_execute(
                arguments.output or CAMPAIGN_RECORD[partition], partition, arguments.groups
            )
        )

    if arguments.model is None:
        raise SystemExit("--stage seal needs --model")
    if arguments.groups is not None and arguments.output is None:
        raise SystemExit("--groups writes a partial record; give it an --output of its own")
    return asyncio.run(
        _stage_seal(arguments.output or SEAL_RECORD, arguments.model, arguments.groups)
    )


if __name__ == "__main__":
    raise SystemExit(main())
