#!/usr/bin/env python
"""S21D3-033 to -037: the fresh v2 self-play campaign, its vertical slice and its snapshots.

One command, because the five items are one ordered pipeline and the order is the evidence:

1. the vertical slice runs one fixture group — outside every scored role — end to end, so a
   defect in the v2 spine is found on a group nobody is allowed to count;
2. every fitting and calibration candidate's *pre-outcome* v2 features are encoded and sealed;
3. only then does the first container start;
4. outcomes are projected under the partition that sealed them;
5. two immutable revision-3 datasets and one fitted matrix are materialised from them.

`seal_feature_records_v2` refuses a seal that is not strictly earlier than the first outcome and
`CorrectionRankingObservationProjector` refuses an outcome that predates its seal, so running
this out of order does not produce a worse campaign — it produces no campaign at all.

What changed from D2 is the encoder, not the pipeline. v2 embeds the alpha-normalised candidate
*source*; the unified diff, the task-requirement embedding and the query-to-candidate cosine are
not inputs any more, so the fitting bounds are fitted over six scalars and 384 named embedding
dimensions rather than over D2's ten.

Storage is the isolated D3 pair from S21D3-002 (`COGOS_DATABASE_URL`, `COGOS_ARTIFACT_ROOT`,
normally from `.env.s21d3.local`). No predecessor store is opened.

    scripts/reality_campaign_d3.py --model <frozen-minilm> --output <evidence.json>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.application.ports.embedding_provider import (  # noqa: E402
    EmbeddingProviderPort,
)
from cognitive_os.application.services.correction_candidate_sequencer import (  # noqa: E402
    AttemptResult,
    AttemptRunner,
    CorrectionCandidateSequencer,
    SequenceMode,
)
from cognitive_os.application.services.correction_ranking_observations import (  # noqa: E402
    CORRECTION_SURFACE,
    CorrectionRankingObservationProjector,
)
from cognitive_os.application.services.learned_datasets import (  # noqa: E402
    ExplicitSelection,
    LearnedDatasetBuilder,
)
from cognitive_os.application.services.learned_evidence import (  # noqa: E402
    LearnedEvidenceService,
)
from cognitive_os.application.services.reality_campaign import (  # noqa: E402
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_campaign_runner import (  # noqa: E402
    ExecutedRun,
    PreparedTask,
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates  # noqa: E402
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder  # noqa: E402
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass  # noqa: E402
from cognitive_os.domain.reality import (  # noqa: E402
    RealityCampaignReceiptManifestV3,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityOutcomeReference,
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
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore  # noqa: E402
from cognitive_os.infrastructure.learned.postgres.repository import (  # noqa: E402
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (  # noqa: E402
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine  # noqa: E402
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore  # noqa: E402
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CANDIDATES_PER_GROUP,
    CatalogueGroup,
    CorpusEntry,
    SealedPartitionCatalogue,
    campaign_manifest_from_groups,
    catalogue_group,
)
from cognitive_os.learning.correction_catalogue_d3 import seal_d3_corpus  # noqa: E402
from cognitive_os.learning.correction_features import (  # noqa: E402
    CANONICAL_EMBEDDING_WINDOW_CHARACTERS,
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
    SealedFeatureRecordV2,
    canonical_embedding_windows,
    feature_input_v2,
    pool_canonical_embedding,
    raw_numeric_row_v2,
    seal_feature_records_v2,
)
from cognitive_os.learning.correction_matrix import (  # noqa: E402
    FittedMatrix,
    FittedRow,
    scan_matrices,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    CorrectionFeatureContractV2,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (  # noqa: E402
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
    NumericBoundsV2,
)
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox  # noqa: E402

from cognitive_os.coding.reality_tasks import GENERATOR_PROFILE_ID  # noqa: E402  isort:skip
from cognitive_os.coding.reality_task_specs_d3 import D3_FIXTURE_SPEC  # noqa: E402  isort:skip

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D3 campaign the same campaign.
D3_CAMPAIGN_NAMESPACE = UUID("b7d61c48-2e05-5a3f-9c14-7f2a8d6b4e93")

#: Task generation is a pure function of the template, the seed and this constant. A clock here
#: would give the same task a new manifest hash on every run, and the manifest hash is what
#: binds an outcome to its task and what a resumed campaign matches against.
GENERATION_EPOCH = datetime(2026, 8, 4, tzinfo=UTC)

D3_VERIFIER_PROFILE_HASH = uuid5(D3_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

#: Every D3 run identity, campaign manifest and projected observation carries this, so a D3
#: outcome can never be replayed into a D2 campaign that happens to plan the same task.
D3_CAMPAIGN_VERSION = 3

FEATURE_SET_MEDIA_TYPE = "application/json"

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

#: The only two partitions this command may open. Final A, final B and canary stay closed until
#: S21D3-059, and the command never resolves a package for them.
_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.CALIBRATION,
)

ACTOR = "reality-campaign-d3"
AUTHORITY = "S21D3-034/035/036"

#: The fixture group S21D3-033 spends. It is in no catalogue, so counting it would be counting
#: a group that no role selected.
FIXTURE_TEMPLATE = D3_FIXTURE_SPEC.template_id
FIXTURE_SEED = 21_033_909


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D3 environment first:\n"
            f"    set -a && . ./.env.s21d3.local && set +a"
        )
    return value


def _git_state() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPOSITORY,
    ).stdout


def _digest(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _implementation_digest() -> str:
    """The v2 spine's own bytes, recorded in every seal so a re-encode is checkable."""
    files = (
        "src/cognitive_os/learning/correction_source.py",
        "src/cognitive_os/learning/correction_features.py",
        "src/cognitive_os/learning/correction_ranking.py",
        "src/cognitive_os/learning/correction_matrix.py",
        "src/cognitive_os/learning/correction_catalogue_d3.py",
    )
    digest = sha256()
    for name in files:
        digest.update((REPOSITORY / name).read_bytes())
    return digest.hexdigest()


def _embedding(model: Path):  # type: ignore[no-untyped-def]
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


_EMBED_BATCH = 64


async def _embed_all(
    embed: EmbeddingProviderPort, texts: tuple[str, ...]
) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        vectors.extend(await embed.embed_documents(texts[start : start + _EMBED_BATCH]))
    return tuple(vectors)


def _windows(candidate_source: str) -> tuple[str, ...]:
    """What v2 embeds: the alpha-normalised AST bytes, in windows the frozen model reads whole."""
    return canonical_embedding_windows(candidate_source)


@dataclass(frozen=True, slots=True)
class _Sequence:
    task_id: UUID
    attempted: int
    unattempted: int
    stop_reason: str


class _Partition:
    """One role's state as it moves through the two passes.

    Groups rather than a catalogue, because S21D3-033's fixture group belongs to no partition
    and `SealedPartitionCatalogue` refuses — correctly — to seal a one-group training role.
    """

    def __init__(
        self,
        *,
        partition: CorrectionPartition,
        manifest_hash: str,
        groups: tuple[CatalogueGroup, ...],
        campaign_id: UUID,
    ) -> None:
        self.partition = partition
        self.manifest_hash = manifest_hash
        self.groups = groups
        self.campaign_id = campaign_id
        self.prepared: dict[str, PreparedTask] = {}
        self.bundles: dict[str, UUID] = {}
        self.task_manifest_hashes: dict[str, str] = {}
        self.pending: list[PendingFeatureV2] = []
        self.rows: list[dict[str, float]] = []
        self.runs: dict[UUID, ExecutedRun] = {}
        self.baselines: list[ExecutedRun] = []
        #: `(observation_id, payload_hash, group, candidate_id, outcome_hash)`
        self.observations: list[tuple[str, str, str, UUID, str]] = []
        self.sequences: list[_Sequence] = []
        self.feature_seal: SealedFeatureRecordSetV2 | None = None
        self.feature_set_artifact: UUID | None = None
        self.receipt_manifest: RealityCampaignReceiptManifestV3 | None = None

    @classmethod
    def from_catalogue(cls, catalogue: SealedPartitionCatalogue) -> _Partition:
        return cls(
            partition=catalogue.partition,
            manifest_hash=catalogue.content_hash,
            groups=catalogue.groups,
            campaign_id=uuid5(D3_CAMPAIGN_NAMESPACE, f"d3:{catalogue.partition.value}"),
        )


async def _seal_features(
    partition: _Partition,
    *,
    runner: RealityCampaignRunner,
    artifacts: ArtifactService,
    scratch: Path,
    embed: EmbeddingProviderPort,
    groups: int | None,
    bundles: dict[str, UUID],
) -> None:
    """Pass one: materialise every package and encode every candidate. No container runs."""
    selected = partition.groups[: groups or len(partition.groups)]
    windows: dict[str, tuple[str, ...]] = {}
    inputs: list[tuple[UUID, UUID, str, str]] = []

    for index, group in enumerate(selected):
        print(
            f"[seal {partition.partition.value} {index + 1}/{len(selected)}] {group.template_id}",
            file=sys.stderr,
        )
        recorded = bundles.get(group.template_id)
        prepared = await runner.prepare_task(
            group.template_id,
            root=scratch / partition.partition.value / group.template_id.replace(".", "_"),
            seed=group.task_seed,
            generated_at=GENERATION_EPOCH,
            bundle_artifact=None if recorded is None else await artifacts.describe(recorded),
        )
        partition.bundles[group.template_id] = prepared.bundle_artifact.artifact_id
        partition.task_manifest_hashes[group.template_id] = prepared.generated.manifest.content_hash
        if prepared.generated.manifest.task_id != group.task_id:
            raise SystemExit(
                f"{group.template_id} generated task {prepared.generated.manifest.task_id}, but "
                f"the sealed catalogue names {group.task_id}"
            )
        partition.prepared[group.template_id] = prepared

        for slot in sorted(group.slots, key=lambda item: item.position):
            recipe = RealityCandidateStrategy(slot.recipe)
            body = reality_candidates.candidate_source(prepared.generated.manifest, recipe)
            windows[str(slot.candidate_id)] = _windows(body)
            inputs.append((slot.candidate_id, group.task_id, group.repository_group, body))

    # One batch over every window of every candidate, then pooled back per candidate, so the
    # number of model calls stays proportional to the corpus rather than to the loop.
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


def _planned_runs(
    partition: _Partition, selected: Sequence[CatalogueGroup]
) -> tuple[RealityRunIdentity, ...]:
    """The identities the runner will mint, derived from the same inputs it derives them from.

    Built before execution because a receipt that is written afterwards records what happened
    rather than what was planned, and S21D3-025 wants the second.
    """
    planned: list[RealityRunIdentity] = []
    for group in selected:
        manifest_hash = partition.task_manifest_hashes[group.template_id]
        for slot in sorted(group.slots, key=lambda item: item.position):
            planned.append(
                RealityRunIdentity(
                    task_id=group.task_id,
                    task_manifest_hash=manifest_hash,
                    run_kind=RealityRunKind.CANDIDATE,
                    candidate_id=slot.candidate_id,
                    strategy=RealityCandidateStrategy(slot.recipe),
                    source=RealityCandidateSource.CURATED,
                    generator_profile_id=GENERATOR_PROFILE_ID,
                    verifier_profile_hash=D3_VERIFIER_PROFILE_HASH,
                    campaign_version=D3_CAMPAIGN_VERSION,
                )
            )
        planned.append(
            RealityRunIdentity(
                task_id=group.task_id,
                task_manifest_hash=manifest_hash,
                run_kind=RealityRunKind.BASELINE,
                source=RealityCandidateSource.BASELINE,
                generator_profile_id=GENERATOR_PROFILE_ID,
                verifier_profile_hash=D3_VERIFIER_PROFILE_HASH,
                campaign_version=D3_CAMPAIGN_VERSION,
            )
        )
    return tuple(planned)


def _receipt_manifest(
    partition: _Partition, selected: Sequence[CatalogueGroup]
) -> RealityCampaignReceiptManifestV3:
    """S21D3-025's durable receipt authority, bound before the first container starts.

    `selection_manifest_hash` is the sealed catalogue: that is what chose these members, and it
    exists at seal time. `selected_member_hashes` are the sealed v2 feature-vector hashes in
    slot order, so a resume that found a different encoding of the same candidate would be
    refused rather than replayed.
    """
    seal = partition.feature_seal
    if seal is None:  # pragma: no cover - callers seal first
        raise SystemExit("a campaign receipt cannot precede its feature seal")
    return RealityCampaignReceiptManifestV3(
        campaign_id=partition.campaign_id,
        campaign_version=D3_CAMPAIGN_VERSION,
        planned_runs=_planned_runs(partition, selected),
        verifier_profile_hash=D3_VERIFIER_PROFILE_HASH,
        created_at=seal.sealed_at,
        partition=partition.partition.value,
        mode="label_all",
        selection_manifest_hash=partition.manifest_hash,
        feature_schema_hash=seal.feature_contract_hash,
        feature_seal_root_hash=seal.content_hash,
        receipt_tasks=tuple(
            RealityReceiptTaskV3(
                task_id=group.task_id,
                task_manifest_hash=partition.task_manifest_hashes[group.template_id],
                bundle_id=partition.bundles[group.template_id],
                bundle_hash=_digest(str(partition.bundles[group.template_id])),
                feature_seal_hash=seal.content_hash,
                candidate_order=tuple(
                    slot.candidate_id for slot in sorted(group.slots, key=lambda s: s.position)
                ),
                selected_member_hashes=tuple(
                    seal.record_for(slot.candidate_id).feature_vector_hash
                    for slot in sorted(group.slots, key=lambda s: s.position)
                ),
            )
            for group in selected
        ),
    )


def _attempt_runner(
    partition: _Partition,
    *,
    runner: RealityCampaignRunner,
    prepared: PreparedTask,
    recipe_of: dict[UUID, RealityCandidateStrategy],
    completed: dict[str, RealityOutcomeReference],
) -> AttemptRunner:
    async def attempt(candidate_id: UUID) -> AttemptResult:
        run = await runner.run_candidate(
            prepared, recipe_of[candidate_id], completed=completed, candidate_id=candidate_id
        )
        partition.runs[candidate_id] = run
        reference = run.step.reference
        return AttemptResult(
            candidate_id=candidate_id,
            accepted=reference.hidden_verification_passed,
            event_id=reference.source_event_id,
            verifier_evidence_hash=reference.hidden_evidence_hash,
        )

    return attempt


async def _execute(
    partition: _Partition,
    *,
    runner: RealityCampaignRunner,
    sequencer: CorrectionCandidateSequencer,
    learned: LearnedEvidenceService,
    completed: dict[str, RealityOutcomeReference],
    groups: int | None,
) -> None:
    """Pass two: run every candidate under `label_all`, then project what the verifier said."""
    selected = partition.groups[: groups or len(partition.groups)]
    seal = partition.feature_seal
    if seal is None:  # pragma: no cover - the caller seals first or there is nothing to run
        raise SystemExit("a partition cannot execute before its features are sealed")
    manifest = campaign_manifest_from_groups(
        selected,
        partition=partition.partition,
        manifest_hash=partition.manifest_hash,
        campaign_id=partition.campaign_id,
        campaign_version=D3_CAMPAIGN_VERSION,
        feature_sealed_at=seal.sealed_at,
    )
    projector = CorrectionRankingObservationProjector(manifest)
    receipt = _receipt_manifest(partition, selected)
    partition.receipt_manifest = receipt

    for index, group in enumerate(selected):
        print(
            f"[run {partition.partition.value} {index + 1}/{len(selected)}] {group.template_id}",
            file=sys.stderr,
        )
        prepared = partition.prepared[group.template_id]
        ordered = sorted(group.slots, key=lambda item: item.position)
        recipe_of = {slot.candidate_id: RealityCandidateStrategy(slot.recipe) for slot in ordered}

        partition.baselines.append(await runner.run_baseline(prepared, completed=completed))

        outcome = await sequencer.run_task(
            campaign_id=partition.campaign_id,
            task_id=group.task_id,
            partition=partition.partition.value,
            mode=SequenceMode.LABEL_ALL,
            campaign_manifest_hash=receipt.content_hash,
            baseline_order=tuple(slot.candidate_id for slot in ordered),
            attempt=_attempt_runner(
                partition,
                runner=runner,
                prepared=prepared,
                recipe_of=recipe_of,
                completed=completed,
            ),
        )
        await sequencer.record(outcome, correlation_id=group.task_id)
        partition.sequences.append(
            _Sequence(
                task_id=group.task_id,
                attempted=len(outcome.attempted_order),
                unattempted=len(outcome.intentionally_unattempted),
                stop_reason=outcome.stop_reason,
            )
        )

        for slot in ordered:
            run = partition.runs[slot.candidate_id]
            observation = projector.project(
                run.step.reference,
                campaign_version=D3_CAMPAIGN_VERSION,
                verifier_profile_hash=group.verifier_profile_hash,
                usage_rights_verified=group.usage_rights_verified,
            )
            stored = await learned.record_observation(
                observation,
                correlation_id=run.step.reference.task_run_id,
                actor=ACTOR,
                authority=AUTHORITY,
            )
            partition.observations.append(
                (
                    str(stored.observation_id),
                    stored.source_payload_hash,
                    group.repository_group,
                    slot.candidate_id,
                    run.step.reference.outcome_hash,
                )
            )


def _partition_report(partition: _Partition) -> dict[str, Any]:
    """Counts read off the recorded references, not off a tally kept while running."""
    references = [run.step.reference for run in partition.runs.values()]
    count = count_outcomes(references)
    accepted = sum(1 for item in references if item.hidden_verification_passed)
    by_recipe: Counter[str] = Counter()
    accepted_by_recipe: Counter[str] = Counter()
    for reference in references:
        label = "" if reference.strategy is None else reference.strategy.value
        by_recipe[label] += 1
        if reference.hidden_verification_passed:
            accepted_by_recipe[label] += 1
    by_position: Counter[int] = Counter()
    accepted_by_position: Counter[int] = Counter()
    for group in partition.groups:
        for slot in group.slots:
            run = partition.runs.get(slot.candidate_id)
            if run is None:
                continue
            by_position[slot.position] += 1
            if run.step.reference.hidden_verification_passed:
                accepted_by_position[slot.position] += 1
    seal = partition.feature_seal
    sealed_at = None if seal is None else seal.sealed_at
    return {
        "partition": partition.partition.value,
        "campaign_id": str(partition.campaign_id),
        "campaign_manifest_hash": partition.manifest_hash,
        "groups_executed": len(partition.baselines),
        "candidate_runs_recorded": len(references),
        "unique_outcomes": count.unique,
        "duplicates_excluded": count.duplicates_excluded,
        "hidden_passed": count.passed,
        "hidden_failed": count.failed,
        "acceptance_rate": round(accepted / len(references), 4) if references else 0.0,
        "baselines_executed": len(partition.baselines),
        "baselines_that_passed_hidden_verification": sum(
            1 for run in partition.baselines if run.hidden_passed
        ),
        "acceptance_by_recipe": {
            name: round(accepted_by_recipe[name] / by_recipe[name], 4) for name in sorted(by_recipe)
        },
        "acceptance_by_position": {
            str(position): round(accepted_by_position[position] / by_position[position], 4)
            for position in sorted(by_position)
        },
        "sequences_recorded": len(partition.sequences),
        "candidates_left_unattempted": sum(item.unattempted for item in partition.sequences),
        "observations_recorded": len(partition.observations),
        "feature_set_artifact_id": str(partition.feature_set_artifact),
        "feature_set_hash": None if seal is None else seal.content_hash,
        "feature_contract_hash": None if seal is None else seal.feature_contract_hash,
        "encoder_version": None if seal is None else seal.encoder_version,
        "normalizer_version": None if seal is None else seal.normalizer_version,
        "features_sealed_at": None if sealed_at is None else sealed_at.isoformat(),
        "first_outcome_at": min(
            (item.occurred_at.isoformat() for item in references), default=None
        ),
        "every_feature_record_precedes_its_outcome": all(
            sealed_at is not None and item.occurred_at > sealed_at for item in references
        ),
        "replayed_runs": sum(1 for run in partition.runs.values() if run.replayed),
        "task_run_ids": [str(item.task_run_id) for item in references]
        + [str(run.step.reference.task_run_id) for run in partition.baselines],
        "bundle_artifacts": {
            template_id: str(artifact_id)
            for template_id, artifact_id in sorted(partition.bundles.items())
        },
        # The exact member table S21D3-039 reads: which candidate, in which group, what the
        # independent verifier said, and which sealed feature record describes it. Recorded
        # here so the selection stage resolves an explicit list rather than querying the store
        # for "everything on this surface".
        "candidate_outcomes": [
            {
                "observation_id": observation_id,
                "candidate_id": str(candidate_id),
                "group": group,
                "accepted": partition.runs[candidate_id].step.reference.hidden_verification_passed,
                "outcome_hash": outcome_hash,
                "payload_hash": payload_hash,
                "feature_vector_hash": (
                    None if seal is None else seal.record_for(candidate_id).feature_vector_hash
                ),
            }
            for observation_id, payload_hash, group, candidate_id, outcome_hash in (
                partition.observations
            )
        ],
    }


def _selection_for(partition: _Partition, *, split: str) -> ExplicitSelection:
    """A revision-3 explicit selection: exact members, exact hashes, one campaign."""
    seal = partition.feature_seal
    if seal is None:  # pragma: no cover - callers seal first
        raise SystemExit("a selection cannot be built before its features are sealed")
    observation_ids = tuple(item[0] for item in partition.observations)
    return ExplicitSelection(
        partition=partition.partition.value,
        members=tuple((item[0], item[1]) for item in partition.observations),
        groups={item[0]: item[2] for item in partition.observations},
        splits={split: observation_ids},
        allowed_provenance=ProvenanceClass.SELF_PLAY,
        identity_revision=3,
        campaign_identity=partition.manifest_hash,
        feature_record_hashes={
            item[0]: seal.record_for(item[3]).feature_vector_hash for item in partition.observations
        },
        outcome_hashes={item[0]: item[4] for item in partition.observations},
        member_content_hashes={
            item[0]: _digest(f"{item[0]}:{item[1]}:{item[4]}") for item in partition.observations
        },
    )


def _fitted_matrix(partition: _Partition, *, split: str) -> FittedMatrix:
    """The rows the scans actually read, built from the seal and the recorded outcomes."""
    seal = partition.feature_seal
    if seal is None:  # pragma: no cover - callers seal first
        raise SystemExit("a matrix cannot be built before its features are sealed")
    rows = []
    for observation_id, _payload, group, candidate_id, _outcome in partition.observations:
        record = seal.record_for(candidate_id)
        run = partition.runs[candidate_id]
        rows.append(
            FittedRow(
                candidate_id=candidate_id,
                task_id=record.task_id,
                group=group,
                partition=partition.partition.value,
                vector=_sealed_vector(record),
                accepted=run.step.reference.hidden_verification_passed,
                sealed_at=seal.sealed_at,
                outcome_at=run.step.reference.occurred_at,
                observation_id=UUID(observation_id),
                sealed_feature_hash=record.feature_vector_hash,
            )
        )
    return FittedMatrix(split=split, rows=tuple(rows))


def _sealed_vector(record: SealedFeatureRecordV2) -> CorrectionFeatureVector:
    """The sealed record's vector, rebuilt without re-encoding anything."""
    return CorrectionFeatureVector(
        encoder_version=record.encoder_version,
        values=record.values,
        embedding=record.embedding,
    )


async def _vertical_slice(
    *,
    runner: RealityCampaignRunner,
    artifacts: ArtifactService,
    sequencer: CorrectionCandidateSequencer,
    learned: LearnedEvidenceService,
    ledger: RealityCampaignLedger,
    builder: LearnedDatasetBuilder,
    embed: EmbeddingProviderPort,
    model_digest: str,
    code_revision: str,
    scratch: Path,
) -> dict[str, Any]:
    """S21D3-033: one fixture group from package to ranking, restart and fallback included."""
    entry = CorpusEntry(
        template_id=D3_FIXTURE_SPEC.template_id,
        repository_group=D3_FIXTURE_SPEC.repository_group,
        family=D3_FIXTURE_SPEC.family.value,
        variants=D3_FIXTURE_SPEC.variants,
        hidden_verifier_source=D3_FIXTURE_SPEC.hidden_test,
        inherited=False,
        module=D3_FIXTURE_SPEC.module,
        module_doc=D3_FIXTURE_SPEC.module_doc,
        imports=D3_FIXTURE_SPEC.imports,
    )
    group = catalogue_group(entry, seed=FIXTURE_SEED)
    fixture_manifest_hash = _digest(f"d3-vertical-slice:{group.content_hash}")
    partition = _Partition(
        partition=CorrectionPartition.TRAINING,
        manifest_hash=fixture_manifest_hash,
        groups=(group,),
        campaign_id=uuid5(D3_CAMPAIGN_NAMESPACE, "d3:vertical-slice"),
    )

    await _seal_features(
        partition,
        runner=runner,
        artifacts=artifacts,
        scratch=scratch,
        embed=embed,
        groups=None,
        bundles={},
    )
    bounds = NumericBoundsV2.from_training(partition.rows)
    seal = seal_feature_records_v2(
        partition.pending,
        partition="training",
        campaign_manifest_hash=fixture_manifest_hash,
        bounds=bounds,
        embedding_model_id=minilm.MODEL_ID,
        embedding_revision=model_digest,
        embedding_tree_digest=model_digest,
        code_revision=code_revision,
        sealed_at=utc_now(),
    )
    partition.feature_seal = seal
    stored = await artifacts.put_bytes(
        seal.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
    )
    partition.feature_set_artifact = stored.artifact_id

    await _execute(
        partition,
        runner=runner,
        sequencer=sequencer,
        learned=learned,
        completed={},
        groups=None,
    )

    selection = _selection_for(partition, split="fit")
    contract = CorrectionFeatureContractV2()
    dataset = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.TRAINING,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )
    replayed = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.TRAINING,
        feature_schema_hash=contract.content_hash,
        revision=3,
        selection=selection,
    )

    matrix = _fitted_matrix(partition, split="fit")
    ordered = sorted(group.slots, key=lambda item: item.position)
    # The slice proves the wiring, not a learned claim: the exemplars are the group's own
    # later rows, which is why the ranking below is reported and never treated as evidence.
    exemplars = tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in matrix.rows[1:])
    knn = CorrectionKnn(exemplars, k=3)
    baseline_order = tuple(str(slot.candidate_id) for slot in ordered)
    ranking = knn.rank(
        {str(row.candidate_id): row.vector for row in matrix.rows},
        baseline_order=baseline_order,
    )

    receipt_manifest = partition.receipt_manifest
    if receipt_manifest is None:  # pragma: no cover - _execute always records one
        raise SystemExit("the vertical slice produced no campaign receipt")
    resumed = await ledger.plan_resume_with_receipts(
        receipt_manifest,
        task_run_ids=[run.step.reference.task_run_id for run in partition.runs.values()],
        campaign_id=partition.campaign_id,
    )

    return {
        "template_id": FIXTURE_TEMPLATE,
        "repository_group": D3_FIXTURE_SPEC.repository_group,
        "in_any_scored_role": False,
        "fixture_manifest_hash": fixture_manifest_hash,
        "campaign_id": str(partition.campaign_id),
        "feature_seal_hash": seal.content_hash,
        "feature_seal_artifact_id": str(stored.artifact_id),
        "features_sealed_at": seal.sealed_at.isoformat(),
        "encoder_version": seal.encoder_version,
        "normalizer_version": seal.normalizer_version,
        "code_revision": seal.code_revision,
        "candidates_executed": len(partition.runs),
        "first_outcome_at": min(
            run.step.reference.occurred_at for run in partition.runs.values()
        ).isoformat(),
        "every_feature_record_precedes_its_outcome": all(
            run.step.reference.occurred_at > seal.sealed_at for run in partition.runs.values()
        ),
        "verifier_decided_every_label": all(
            run.step.reference.hidden_evidence_hash for run in partition.runs.values()
        ),
        "accepted_candidates": sum(
            run.step.reference.hidden_verification_passed for run in partition.runs.values()
        ),
        "observations_projected": len(partition.observations),
        "dataset_id": str(dataset.dataset_id),
        "dataset_identity_revision": 3,
        "split_manifest_hash": dataset.split_manifest_hash,
        "rebuilt_identically": str(replayed.dataset_id) == str(dataset.dataset_id)
        and replayed.content_hash == dataset.content_hash,
        "fitted_matrix_hash": matrix.content_hash,
        "fitted_columns": len(matrix.column_names),
        "ranking": {
            "abstained": ranking.abstained,
            "reason": ranking.reason,
            "confidence": str(ranking.confidence),
            "first_choice": ranking.first_choice,
            "baseline_first_choice": baseline_order[0],
            "order_equals_baseline": ranking.ordered_candidate_ids == baseline_order,
            "prediction_accepted_nothing": True,
        },
        "receipt_manifest_hash": receipt_manifest.content_hash,
        "receipt_effective_remainder": [str(item) for item in resumed.effective_remainder],
        "receipt_is_resumable": resumed.is_resumable,
        "final_capability_present": False,
        "retrieval_capability_present": False,
        "canary_capability_present": False,
    }


async def _resume_report(ledger: RealityCampaignLedger, partition: _Partition) -> dict[str, Any]:
    """Ask the durable receipt whether the partition is complete. Never ask this process."""
    manifest = partition.receipt_manifest
    if manifest is None:  # pragma: no cover - _execute always records one
        raise SystemExit("a resume report needs the receipt the campaign was recorded under")
    task_run_ids = [item.step.reference.task_run_id for item in partition.runs.values()]
    task_run_ids += [item.step.reference.task_run_id for item in partition.baselines]
    plan = await ledger.plan_resume_with_receipts(
        manifest, task_run_ids=task_run_ids, campaign_id=partition.campaign_id
    )
    return {
        "receipt_manifest_hash": manifest.content_hash,
        "selection_manifest_hash": manifest.selection_manifest_hash,
        "feature_seal_root_hash": manifest.feature_seal_root_hash,
        "planned": len(manifest.planned_runs),
        "completed": len(plan.plan.completed),
        "remaining": len(plan.plan.remaining),
        "effective_remainder": len(plan.effective_remainder),
        "is_complete": plan.plan.is_complete,
        "is_resumable": plan.is_resumable,
        "refused": [str(item) for item in plan.refused],
        "actions": dict(Counter(item.action.value for item in plan.tasks)),
    }


async def _snapshots(
    partitions: dict[CorrectionPartition, _Partition], *, builder: LearnedDatasetBuilder
) -> dict[str, Any]:
    """S21D3-037: two separate immutable datasets and one matrix built from fitting alone."""
    contract = CorrectionFeatureContractV2()
    fitting = partitions[CorrectionPartition.TRAINING]
    calibration = partitions[CorrectionPartition.CALIBRATION]
    selections = {
        "fitting": _selection_for(fitting, split="fit"),
        "calibration": _selection_for(calibration, split="calibration"),
    }
    records = {}
    for name, selection in selections.items():
        # Both datasets are `training` corpus material: they are self-play, and the released
        # enum's other value is `evaluation`, which calibration is not. What separates them is
        # revision-3 identity — partition, split and selection digest — so no new corpus role
        # and therefore no migration is needed to keep them two immutable datasets.
        record = await builder.build(
            surface=CORRECTION_SURFACE,
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=contract.content_hash,
            revision=3,
            selection=selection,
        )
        replayed = await builder.build(
            surface=CORRECTION_SURFACE,
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=contract.content_hash,
            revision=3,
            selection=selection,
        )
        records[name] = {
            "dataset_id": str(record.dataset_id),
            "corpus_role": record.corpus_role.value,
            "partition": selection.partition,
            "split": "fit" if name == "fitting" else "calibration",
            "identity_revision": 3,
            "observation_count": record.observation_count,
            "provenance_counts": record.provenance_counts,
            "real_governed_runs": record.provenance_counts.get("real_governed_run", 0),
            "example_manifest_hash": record.example_manifest_hash,
            "split_manifest_hash": record.split_manifest_hash,
            "usage_rights_verified": record.usage_rights_verified,
            "rebuilt_identically": str(replayed.dataset_id) == str(record.dataset_id)
            and replayed.content_hash == record.content_hash,
            "groups": len(
                {item[2] for item in (fitting if name == "fitting" else calibration).observations}
            ),
        }

    fit_matrix = _fitted_matrix(fitting, split="fit")
    calibration_matrix = _fitted_matrix(calibration, split="calibration")
    report = scan_matrices(fit_matrix, calibration_matrix, created_at=utc_now(), contract=contract)
    return {
        "datasets": records,
        "selections": {
            name: {
                "members": len(selection.members),
                "campaign_identity": selection.campaign_identity,
                "store_wide_selection": False,
                "latest_seal_selection": False,
            }
            for name, selection in selections.items()
        },
        "fitted_matrix": {
            "fit_matrix_hash": report.fit_matrix_hash,
            "calibration_matrix_hash": report.calibration_matrix_hash,
            "fit_rows": report.fit_rows,
            "calibration_rows": report.calibration_rows,
            "fit_groups": report.fit_groups,
            "calibration_groups": report.calibration_groups,
            "fitted_dimensions": len(report.column_names),
            "encoder_version": report.encoder_version,
            "feature_contract_hash": report.feature_contract_hash,
            "maximum_cross_split_similarity": report.maximum_cross_split_similarity,
            "clean": report.clean,
            "report_hash": report.content_hash,
            "scans": [
                {"name": scan.name, "passed": scan.passed, "detail": scan.detail}
                for scan in report.scans
            ],
        },
        "fit_and_calibration_share_no_group": not (fit_matrix.groups & calibration_matrix.groups),
    }


async def _run(
    output: Path, slice_output: Path, model: Path, group_limit: int | None, resume_from: Path | None
) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1", "s21d2"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D3 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")

    tree_before = _git_state()
    engine = create_postgres_engine(database_url)
    started = utc_now()
    code_revision = _implementation_digest()
    report: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W2",
        "items": ["S21D3-033", "S21D3-034", "S21D3-035", "S21D3-036", "S21D3-037"],
        "final_outcomes_inspected": False,
    }
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        coding_events = CodingEventService(events)
        recorder = CodingOutcomeRecorder(artifacts, coding_events, events)
        repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))
        ledger = RealityCampaignLedger(events)
        sequencer = CorrectionCandidateSequencer(coding_events)
        builder = LearnedDatasetBuilder(repository, LearnedArtifactStore(artifacts))
        runner = RealityCampaignRunner(
            sandbox=DockerSandbox(SANDBOX_IMAGE),
            artifacts=artifacts,
            recorder=recorder,
            harvester=None,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=D3_VERIFIER_PROFILE_HASH,
            campaign_version=D3_CAMPAIGN_VERSION,
        )
        embed, model_digest = _embedding(model)

        report["store_before_campaign"] = {
            "correction_ranking_observations": len(
                await learned.list_observations(surface=CORRECTION_SURFACE, limit=1000)
            ),
            "note": "prior rows in the isolated D3 pair; explicit selection makes them irrelevant",
        }

        bundle = seal_d3_corpus()
        completed: dict[str, RealityOutcomeReference] = {}
        bundles: dict[CorrectionPartition, dict[str, UUID]] = {name: {} for name in _ORDER}
        sealed_before: dict[CorrectionPartition, tuple[datetime, str, UUID]] = {}
        if resume_from is not None:
            previous = json.loads(resume_from.read_text(encoding="utf-8"))
            identities = [
                UUID(item) for entry in previous["partitions"] for item in entry["task_run_ids"]
            ]
            completed = dict(await ledger.completed_by_identity(identities))
            for entry in previous["partitions"]:
                name = CorrectionPartition(entry["partition"])
                bundles[name] = {
                    template_id: UUID(artifact_id)
                    for template_id, artifact_id in entry.get("bundle_artifacts", {}).items()
                }
                if entry.get("features_sealed_at"):
                    sealed_before[name] = (
                        datetime.fromisoformat(entry["features_sealed_at"]),
                        entry["feature_set_hash"],
                        UUID(entry["feature_set_artifact_id"]),
                    )
        report["resumed_from"] = {
            "file": None if resume_from is None else resume_from.as_posix(),
            "already_recorded_run_identities": len(completed),
        }
        if resume_from is not None and "vertical_slice" in previous:
            # The slice is spent once. Re-running it on a resume would execute a second set of
            # containers for a group whose evidence already exists.
            report["vertical_slice"] = previous["vertical_slice"]

        partitions = {name: _Partition.from_catalogue(bundle.catalogues[name]) for name in _ORDER}
        bounds: NumericBoundsV2 | None = None
        with tempfile.TemporaryDirectory(prefix="cogos-d3-campaign-") as scratch:
            if resume_from is None:
                slice_report = await _vertical_slice(
                    runner=runner,
                    artifacts=artifacts,
                    sequencer=sequencer,
                    learned=learned,
                    ledger=ledger,
                    builder=builder,
                    embed=embed,
                    model_digest=model_digest,
                    code_revision=code_revision,
                    scratch=Path(scratch),
                )
                slice_output.parent.mkdir(parents=True, exist_ok=True)
                slice_output.write_text(
                    json.dumps(slice_report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                report["vertical_slice"] = slice_report

            for name in _ORDER:
                partition = partitions[name]
                await _seal_features(
                    partition,
                    runner=runner,
                    artifacts=artifacts,
                    scratch=Path(scratch),
                    embed=embed,
                    groups=group_limit,
                    bundles=bundles[name],
                )
                # Fitted on fitting and reused, never refitted per partition: bounds fitted on
                # calibration would carry calibration statistics into the encoder, which is a
                # leak no feature-name check would ever catch.
                if bounds is None:
                    bounds = NumericBoundsV2.from_training(partition.rows)
                previously = sealed_before.get(name)
                sealed = seal_feature_records_v2(
                    partition.pending,
                    partition=name.value,
                    campaign_manifest_hash=partition.manifest_hash,
                    bounds=bounds,
                    embedding_model_id=minilm.MODEL_ID,
                    embedding_revision=model_digest,
                    embedding_tree_digest=model_digest,
                    code_revision=code_revision,
                    sealed_at=utc_now() if previously is None else previously[0],
                )
                if previously is not None and sealed.content_hash != previously[1]:
                    raise SystemExit(
                        f"the {name.value} v2 feature set no longer reproduces the seal it was "
                        f"executed under ({previously[1]} -> {sealed.content_hash}); the corpus, "
                        "the bounds, the normaliser or the embedding changed and this is a "
                        "different campaign wearing the same identity"
                    )
                partition.feature_seal = sealed
                stored = (
                    await artifacts.put_bytes(
                        sealed.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
                    )
                    if previously is None
                    else None
                )
                partition.feature_set_artifact = (
                    previously[2] if stored is None else stored.artifact_id
                )

            for name in _ORDER:
                await _execute(
                    partitions[name],
                    runner=runner,
                    sequencer=sequencer,
                    learned=learned,
                    completed=completed,
                    groups=group_limit,
                )

        report["partitions"] = [_partition_report(partitions[name]) for name in _ORDER]
        snapshot = await _snapshots(partitions, builder=builder)
        report["snapshot"] = snapshot
        report["resume"] = {
            name.value: await _resume_report(ledger, partitions[name]) for name in _ORDER
        }
        report["group_disjointness"] = {
            "fitting_groups": len(bundle.groups_of(CorrectionPartition.TRAINING)),
            "calibration_groups": len(bundle.groups_of(CorrectionPartition.CALIBRATION)),
            "fitting_shared_with_calibration": sorted(
                bundle.groups_of(CorrectionPartition.TRAINING)
                & bundle.groups_of(CorrectionPartition.CALIBRATION)
            ),
            "calibration_shared_with_final_a": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.FINAL_A)
            ),
            "calibration_shared_with_final_b": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.FINAL_B)
            ),
            "calibration_shared_with_canary": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.CANARY)
            ),
            "calibration_shared_with_retrieval": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION) & bundle.retrieval_groups
            ),
            "inherited_groups_in_calibration": [
                group.repository_group
                for group in bundle.catalogues[CorrectionPartition.CALIBRATION].groups
                if group.inherited_from_d1
            ],
        }
        report["provenance"] = {
            "real_governed_run_observations_written": 0,
            "final_batch_a_opened": False,
            "final_batch_b_opened": False,
            "canary_opened": False,
            "retrieval_holdout_opened": False,
            "candidates_per_group": CANDIDATES_PER_GROUP,
        }
        report["storage"] = {
            "database": database_url.rsplit("/", 1)[-1],
            "artifact_root": str(artifact_root),
            "predecessor_store_writes": 0,
        }
        report["embedding"] = {
            "model_id": minilm.MODEL_ID,
            "tree_digest": model_digest,
            "dimension": minilm.DIMENSION,
            "provider": "sentence_transformers, local frozen model, no network",
            "embedded_text": "alpha-normalised canonical candidate source (v2)",
            "window_characters": CANONICAL_EMBEDDING_WINDOW_CHARACTERS,
            "pooling": "mean over windows, renormalised onto the unit sphere",
        }
        report["code_revision"] = code_revision
        report["d3_seal_hash"] = bundle.seal.content_hash
        report["main_worktree_mutations"] = 0 if _git_state() == tree_before else "CHANGED"
        report["started_at"] = started.isoformat()
        report["finished_at"] = utc_now().isoformat()
        report["recorded_at"] = utc_now().isoformat()
    finally:
        await engine.dispose()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.as_posix())
    return 0 if report["main_worktree_mutations"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vertical-slice-output", type=Path, required=True)
    parser.add_argument(
        "--model",
        type=Path,
        default=Path(os.environ.get("COGOS_LOCAL_EMBEDDING_MODEL_PATH", "models/all-MiniLM-L6-v2")),
    )
    parser.add_argument("--groups", type=int, default=None, help="limit groups per partition")
    parser.add_argument("--resume-from", type=Path)
    arguments = parser.parse_args()
    return asyncio.run(
        _run(
            arguments.output,
            arguments.vertical_slice_output,
            arguments.model,
            arguments.groups,
            arguments.resume_from,
        )
    )


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
