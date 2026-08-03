"""Run the Sprint 21D2 self-play campaign over the sealed training and calibration partitions.

One operator command drives S21D2-023, 024 and 025, because they are one pipeline: features
are sealed, candidates are executed, outcomes are projected under the partition that sealed
them, and the two partitions become one immutable training snapshot with disjoint `fit` and
`calibration` splits. Every count in the report is read back out of what was persisted.

The order inside a partition is not an implementation detail:

1. every task package is materialised and every candidate's *pre-outcome* features are
   encoded and sealed into one hash-bound artifact;
2. only then does the first container start.

That is what makes "every feature record precedes its outcome" a fact about the wall clock
rather than a claim about intent — `CorrectionRankingObservationProjector` refuses an outcome
that predates the seal, so a campaign run in the wrong order cannot produce an observation.

Storage is the isolated D2 pair from S21D2-002 (`COGOS_DATABASE_URL` and
`COGOS_ARTIFACT_ROOT`, normally from `.env.s21d2.local`). The development pair and the C3 and
D1 stores are never opened.

    scripts/reality_campaign_d2.py --model <frozen-minilm> --output docs/.../evidence.json

Resume is safe: with `--resume-from`, run identities the Event Store already holds are skipped
and their stored outcome references are reused as-is.
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
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderPort,
)
from cognitive_os.application.services.correction_candidate_sequencer import (
    AttemptResult,
    AttemptRunner,
    CorrectionCandidateSequencer,
    SequenceMode,
)
from cognitive_os.application.services.correction_ranking_observations import (
    CORRECTION_SURFACE,
    CorrectionRankingObservationProjector,
)
from cognitive_os.application.services.learned_datasets import (
    ExplicitSelection,
    LearnedDatasetBuilder,
)
from cognitive_os.application.services.learned_evidence import (
    LearnedEvidenceService,
)
from cognitive_os.application.services.reality_campaign import (
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_campaign_runner import (
    ExecutedRun,
    PreparedTask,
    RealityCampaignRunner,
)
from cognitive_os.coding import reality_candidates
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import template
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityCandidateStrategy,
    RealityOutcomeReference,
)
from cognitive_os.domain.sandbox import SandboxLimits
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.infrastructure.artifacts.filesystem import (
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.learning import calibration_ood
from cognitive_os.learning.correction_catalogue import (
    CANDIDATES_PER_GROUP,
    SealedPartitionCatalogue,
    campaign_manifest_for,
    seal_corpus,
)
from cognitive_os.learning.correction_features import (
    PendingFeature,
    feature_input,
    raw_numeric_row,
    requirement_text,
    seal_feature_records,
)
from cognitive_os.learning.correction_protocol import (
    CorrectionFeatureContract,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import NumericBounds
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

#: Fixed forever: it is what makes a resumed D2 campaign the same campaign.
D2_CAMPAIGN_NAMESPACE = UUID("c4a1e7b9-3d52-5f68-9021-6b8e4d3a7f15")

#: Task generation is a pure function of the template, the seed and this constant. Reading a
#: clock here would give the same task a new manifest hash on every run, and the manifest hash
#: is what binds an outcome to its task and what a resumed campaign matches against.
GENERATION_EPOCH = datetime(2026, 8, 2, tzinfo=UTC)

#: The D2 verifier profile every run in this campaign was measured against, recorded in each
#: run identity so a resumed campaign cannot silently mix two verifier revisions. Distinct from
#: `CatalogueGroup.verifier_profile_hash`, which is the hash of one group's own hidden suite:
#: that one binds a group to the bytes that judge it, this one binds a campaign to a revision
#: of the verifier itself. Both are checked, in the two places where they mean something.
D2_VERIFIER_PROFILE_HASH = uuid5(D2_CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

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

#: The partitions this command may run, in the only order that is correct: the numeric bounds
#: are fitted on training and reused for calibration, so calibration cannot be sealed first.
_ORDER: tuple[CorrectionPartition, ...] = (
    CorrectionPartition.TRAINING,
    CorrectionPartition.CALIBRATION,
)

ACTOR = "reality-campaign-d2"
AUTHORITY = "S21D2-023/024"

#: What this wave found while running, recorded in the evidence rather than only in a commit
#: message, because a finding that lives in history is a finding nobody reads.
FINDINGS: tuple[dict[str, str], ...] = (
    {
        "id": "W4-F1",
        "subject": "RealityCampaignSequenceRecorded",
        "observed": (
            "The event was declared below CODING_EVENT_MODELS in the same module, so the "
            "default catalog never registered it and PostgresEventStore.append refused it as "
            "an unsupported contract. Sprint 21D2's campaign receipt — the durable authority "
            "for what a stop-first campaign deliberately did not do — could not be appended to "
            "a real Event Store at all. The W2 and W3c tests exercised the sequencer against "
            "an in-memory recording double, which is why it looked complete."
        ),
        "action": (
            "The tuple now sits below every model it names and includes the receipt. The "
            "exported contract schemas were regenerated; the drift gate caught the addition."
        ),
        "status": "fixed",
    },
    {
        "id": "W4-F2",
        "subject": "this command's resume path",
        "observed": (
            "The first resume re-executed all three hundred containers instead of replaying "
            "them. prepare_task minted a fresh control-bundle artifact, the task manifest "
            "names its bundle by artifact ID, and the run identity hashes the manifest — so "
            "every run got a new identity and completed_by_identity matched nothing. The C3 "
            "campaign had already learned this and passed its bundles back; this one did not."
        ),
        "action": (
            "Bundle artifact IDs are recorded per partition and passed back on resume. A "
            "runner test pins the identity: the recorded bundle reproduces the run identity "
            "and a re-minted one does not."
        ),
        "status": "fixed",
    },
    {
        "id": "W4-F3",
        "subject": "the sealed feature record set across a resume",
        "observed": (
            "With W4-F2 fixed, the resume replayed every run and then refused to project any "
            "of them: the outcomes carry their original execution times and the feature set "
            "had been re-sealed with the current clock, so every outcome preceded its own "
            "feature record. The projector was right. A resume that re-seals features has "
            "not resumed the campaign, it has produced post-outcome features for it."
        ),
        "action": (
            "The recorded seal time is carried across the resume and the re-encoded set must "
            "reproduce the recorded hash, so a corpus, bounds or embedding change is refused "
            "rather than silently re-sealed."
        ),
        "status": "fixed",
    },
)

DEVIATIONS: tuple[dict[str, str], ...] = (
    {
        "id": "W4-D1",
        "subject": "duplicated self-play observations in the isolated D2 store",
        "observed": (
            "W4-F2 means the same two hundred and forty candidates were executed twice, under "
            "two sets of run identities, so the store holds four hundred and eighty accepted "
            "correction-ranking observations for two hundred and forty distinct pieces of "
            "work. Both executions are real: every row resolves to bytes and to an event."
        ),
        "action": (
            "Not deleted. store_before_campaign records the count this run inherited, and the "
            "training snapshot selects an explicit member list rather than whatever the store "
            "holds, so the dataset is exactly two hundred and forty observations regardless. "
            "Erasing rows to make a total look round is what turns evidence into a claim."
        ),
    },
)


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated D2 environment first:\n"
            f"    set -a && . ./.env.s21d2.local && set +a"
        )
    return value


def _git_state() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout


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


#: `EmbeddingProviderPort` refuses a batch above the configured maximum, and one campaign
#: embeds a few hundred texts. Chunking here rather than raising the maximum keeps the
#: provider's own bound meaningful.
_EMBED_BATCH = 64


async def _embed_all(
    embed: EmbeddingProviderPort, texts: tuple[str, ...]
) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        vectors.extend(await embed.embed_documents(texts[start : start + _EMBED_BATCH]))
    return tuple(vectors)


@dataclass(frozen=True, slots=True)
class _Sequence:
    """One recorded campaign receipt, as the report counts it."""

    task_id: UUID
    attempted: int
    unattempted: int
    stop_reason: str


class _Partition:
    """One partition's state as it moves through the two passes."""

    def __init__(self, catalogue: SealedPartitionCatalogue) -> None:
        self.catalogue = catalogue
        self.campaign_id = uuid5(D2_CAMPAIGN_NAMESPACE, f"d2:{catalogue.partition.value}")
        self.prepared: dict[str, PreparedTask] = {}
        #: `template_id -> control bundle artifact`, carried across a resume. See W4-F2.
        self.bundles: dict[str, UUID] = {}
        self.pending: list[PendingFeature] = []
        self.rows: list[dict[str, float]] = []
        self.runs: dict[UUID, ExecutedRun] = {}
        self.baselines: list[ExecutedRun] = []
        self.observations: list[tuple[str, str, str]] = []
        self.sequences: list[_Sequence] = []
        self.feature_set_artifact: UUID | None = None
        self.feature_set_hash: str | None = None
        self.feature_sealed_at: datetime | None = None


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
    catalogue = partition.catalogue
    selected = catalogue.groups[: groups or len(catalogue.groups)]
    texts: dict[str, str] = {}
    inputs: list[tuple[UUID, UUID, str, str, str, str]] = []

    for index, group in enumerate(selected):
        print(
            f"[seal {catalogue.partition.value} {index + 1}/{len(selected)}] {group.template_id}",
            file=sys.stderr,
        )
        # W4-F2. The control bundle artifact has to be the one the first run recorded. The
        # Artifact Store mints a fresh metadata row for identical bytes, the task manifest names
        # its bundle by artifact ID, and the run identity hashes the manifest — so re-minting it
        # gives every run a new identity and a resume matches nothing, silently re-executing the
        # whole campaign. C3 learned this and passed its bundles back; this command did not, and
        # its first resume cost three hundred containers to prove it.
        recorded = bundles.get(group.template_id)
        prepared = await runner.prepare_task(
            group.template_id,
            root=scratch / catalogue.partition.value / group.template_id.replace(".", "_"),
            seed=group.task_seed,
            generated_at=GENERATION_EPOCH,
            bundle_artifact=None if recorded is None else await artifacts.describe(recorded),
        )
        partition.bundles[group.template_id] = prepared.bundle_artifact.artifact_id
        if prepared.generated.manifest.task_id != group.task_id:
            raise SystemExit(
                f"{group.template_id} generated task {prepared.generated.manifest.task_id}, but "
                f"the sealed catalogue names {group.task_id}"
            )
        partition.prepared[group.template_id] = prepared
        item = template(group.template_id)
        task_text = requirement_text(item.issue_description, item.expected_behavior)
        texts[f"task:{group.template_id}"] = task_text

        for slot in sorted(group.slots, key=lambda item: item.position):
            recipe = RealityCandidateStrategy(slot.recipe)
            candidate = reality_candidates.build_candidate(
                prepared.generated.manifest, recipe, candidate_id=slot.candidate_id
            )
            body = reality_candidates.candidate_source(prepared.generated.manifest, recipe)
            texts[f"cand:{slot.candidate_id}"] = candidate.unified_diff
            inputs.append(
                (
                    slot.candidate_id,
                    group.task_id,
                    group.template_id,
                    group.repository_group,
                    body,
                    candidate.unified_diff,
                )
            )

    keys = sorted(texts)
    vectors = await _embed_all(embed, tuple(texts[key] for key in keys))
    embedded = dict(zip(keys, vectors, strict=True))

    for candidate_id, task_id, template_id, group_name, body, diff in inputs:
        features = feature_input(
            candidate_source=body,
            unified_diff=diff,
            task_requirement_embedding=embedded[f"task:{template_id}"],
            candidate_delta_embedding=embedded[f"cand:{candidate_id}"],
        )
        partition.rows.append(raw_numeric_row(features))
        partition.pending.append(
            PendingFeature(
                candidate_id=candidate_id,
                task_id=task_id,
                repository_group=group_name,
                features=features,
            )
        )


def _attempt_runner(
    partition: _Partition,
    *,
    runner: RealityCampaignRunner,
    prepared: PreparedTask,
    recipe_of: dict[UUID, RealityCandidateStrategy],
    completed: dict[str, RealityOutcomeReference],
) -> AttemptRunner:
    """One task's attempt callable, built outside the loop so it binds one task's values.

    The sequencer decides which candidate runs next; this is the only thing that runs one.
    """

    async def attempt(candidate_id: UUID) -> AttemptResult:
        run = await runner.run_candidate(
            prepared,
            recipe_of[candidate_id],
            completed=completed,
            candidate_id=candidate_id,
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
    catalogue = partition.catalogue
    selected = catalogue.groups[: groups or len(catalogue.groups)]
    manifest = campaign_manifest_for(
        catalogue,
        campaign_id=partition.campaign_id,
        campaign_version=1,
        feature_sealed_at=partition.feature_sealed_at,
    )
    projector = CorrectionRankingObservationProjector(manifest)

    for index, group in enumerate(selected):
        print(
            f"[run {catalogue.partition.value} {index + 1}/{len(selected)}] {group.template_id}",
            file=sys.stderr,
        )
        prepared = partition.prepared[group.template_id]
        ordered = sorted(group.slots, key=lambda item: item.position)
        recipe_of = {slot.candidate_id: RealityCandidateStrategy(slot.recipe) for slot in ordered}

        baseline = await runner.run_baseline(prepared, completed=completed)
        partition.baselines.append(baseline)

        attempt = _attempt_runner(
            partition,
            runner=runner,
            prepared=prepared,
            recipe_of=recipe_of,
            completed=completed,
        )

        outcome = await sequencer.run_task(
            campaign_id=partition.campaign_id,
            task_id=group.task_id,
            partition=catalogue.partition.value,
            mode=SequenceMode.LABEL_ALL,
            campaign_manifest_hash=catalogue.content_hash,
            baseline_order=tuple(slot.candidate_id for slot in ordered),
            attempt=attempt,
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
                campaign_version=1,
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
                (str(stored.observation_id), stored.source_payload_hash, group.repository_group)
            )


def _partition_report(partition: _Partition) -> dict[str, object]:
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
    for group in partition.catalogue.groups:
        for slot in group.slots:
            run = partition.runs.get(slot.candidate_id)
            if run is None:
                continue
            by_position[slot.position] += 1
            if run.step.reference.hidden_verification_passed:
                accepted_by_position[slot.position] += 1
    return {
        "partition": partition.catalogue.partition.value,
        "campaign_id": str(partition.campaign_id),
        "campaign_manifest_hash": partition.catalogue.content_hash,
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
        "feature_set_hash": partition.feature_set_hash,
        "features_sealed_at": (
            None if partition.feature_sealed_at is None else partition.feature_sealed_at.isoformat()
        ),
        "first_outcome_at": min(
            (item.occurred_at.isoformat() for item in references), default=None
        ),
        "every_feature_record_precedes_its_outcome": all(
            partition.feature_sealed_at is not None
            and item.occurred_at >= partition.feature_sealed_at
            for item in references
        ),
        "replayed_runs": sum(1 for run in partition.runs.values() if run.replayed),
        "task_run_ids": [str(item.task_run_id) for item in references]
        + [str(run.step.reference.task_run_id) for run in partition.baselines],
        "bundle_artifacts": {
            template_id: str(artifact_id)
            for template_id, artifact_id in sorted(partition.bundles.items())
        },
    }


async def _resolve_calibration_ood(
    calibration: _Partition, *, artifacts: ArtifactService, submanifest_hash: str, seed: int
) -> dict[str, object]:
    """S21D2-024: turn the presealed perturbations into inputs, and prove they still run."""
    tasks: list[calibration_ood.PerturbedTask] = []
    for group in calibration.catalogue.groups[: len(calibration.baselines)]:
        item = template(group.template_id)
        module_path = next(path for path in item.visible_files if path.startswith("src/"))
        visible_path = next(path for path in item.visible_files if path.startswith("tests/"))
        hidden_path = next(path for path in item.control_files if path.startswith("test_hidden"))
        perturbed = calibration_ood.perturb(
            module_source=item.visible_files[module_path],
            visible_test=item.visible_files[visible_path],
            hidden_test=item.control_files[hidden_path],
            issue=item.issue_description,
        )
        passes = _visible_suite_passes(
            module_name=module_path.removeprefix("src/"),
            module_source=perturbed.module_source,
            visible_test=perturbed.visible_test,
        )
        applied = tuple(item.name for item in perturbed.applied if item.applied)
        absent = tuple(item.name for item in perturbed.applied if not item.applied)
        tasks.append(
            calibration_ood.PerturbedTask(
                template_id=group.template_id,
                repository_group=group.repository_group,
                perturbations_applied=applied,
                perturbations_not_applicable=absent,
                module_source_hash=sha256(perturbed.module_source.encode()).hexdigest(),
                visible_test_hash=sha256(perturbed.visible_test.encode()).hexdigest(),
                issue_text_hash=sha256(perturbed.issue.encode()).hexdigest(),
                visible_suite_passes=passes,
            )
        )
    resolved = calibration_ood.ResolvedOodSet(
        kind="calibration_precheck",
        submanifest_hash=submanifest_hash,
        perturbation_seed=seed,
        tasks=tuple(tasks),
    )
    stored = await artifacts.put_bytes(
        resolved.canonical_json().encode(), media_type=FEATURE_SET_MEDIA_TYPE
    )
    return {
        "artifact_id": str(stored.artifact_id),
        "content_hash": resolved.content_hash,
        "submanifest_hash": submanifest_hash,
        "tasks_resolved": len(tasks),
        "perturbations_applied": dict(
            Counter(name for task in tasks for name in task.perturbations_applied)
        ),
        "perturbations_not_applicable": dict(
            Counter(name for task in tasks for name in task.perturbations_not_applicable)
        ),
        "perturbed_packages_that_still_execute": sum(
            1 for task in tasks if task.visible_suite_passes
        ),
        "retained_outside_fitting": True,
        "entered_any_dataset": False,
    }


def _visible_suite_passes(*, module_name: str, module_source: str, visible_test: str) -> bool:
    """Execute one perturbed package's published suite. A probe that cannot run is not one."""
    with tempfile.TemporaryDirectory(prefix="cogos-d2-ood-") as directory:
        root = Path(directory)
        (root / module_name).write_text(module_source, encoding="utf-8")
        (root / "test_visible.py").write_text(visible_test, encoding="utf-8")
        completed = subprocess.run(  # fixed argv, no shell, throwaway directory
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_visible.py"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        return completed.returncode == 0


async def _snapshot(
    partitions: dict[CorrectionPartition, _Partition],
    *,
    builder: LearnedDatasetBuilder,
    feature_schema_hash: str,
) -> dict[str, object]:
    """S21D2-025: one training dataset whose `fit` and `calibration` splits share no group."""
    training = partitions[CorrectionPartition.TRAINING]
    calibration = partitions[CorrectionPartition.CALIBRATION]
    members = tuple(
        (observation_id, payload_hash)
        for observation_id, payload_hash, _ in training.observations + calibration.observations
    )
    groups = {
        observation_id: group
        for observation_id, _, group in training.observations + calibration.observations
    }
    selection = ExplicitSelection(
        partition="d2-training-snapshot",
        members=members,
        groups=groups,
        splits={
            "fit": tuple(item[0] for item in training.observations),
            "calibration": tuple(item[0] for item in calibration.observations),
        },
        allowed_provenance=ProvenanceClass.SELF_PLAY,
    )
    record = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.TRAINING,
        feature_schema_hash=feature_schema_hash,
        selection=selection,
    )
    # Built a second time from the same inputs: an immutable snapshot that produced a second
    # identity would not be one, and the builder returning the stored record is the proof.
    replayed = await builder.build(
        surface=CORRECTION_SURFACE,
        corpus_role=CorpusRole.TRAINING,
        feature_schema_hash=feature_schema_hash,
        selection=selection,
    )
    return {
        "dataset_id": str(record.dataset_id),
        "corpus_role": record.corpus_role.value,
        "split_policy": "explicit-partition-manifest",
        "observation_count": record.observation_count,
        "fit_observations": len(training.observations),
        "calibration_observations": len(calibration.observations),
        "provenance_counts": record.provenance_counts,
        "real_governed_runs_in_training": record.provenance_counts.get("real_governed_run", 0),
        "example_manifest_hash": record.example_manifest_hash,
        "split_manifest_hash": record.split_manifest_hash,
        "usage_rights_verified": record.usage_rights_verified,
        "rebuilt_identically": str(replayed.dataset_id) == str(record.dataset_id)
        and replayed.content_hash == record.content_hash,
        "fit_and_calibration_share_no_group": not (
            {group for _, _, group in training.observations}
            & {group for _, _, group in calibration.observations}
        ),
    }


async def _resume_report(ledger: RealityCampaignLedger, partition: _Partition) -> dict[str, object]:
    """Ask the durable records whether the partition is complete. Never ask this process."""
    planned = [run.identity for run in partition.runs.values()]
    planned += [run.identity for run in partition.baselines]
    task_run_ids = [item.step.reference.task_run_id for item in partition.runs.values()]
    task_run_ids += [item.step.reference.task_run_id for item in partition.baselines]
    manifest = RealityCampaignManifest(
        campaign_id=partition.campaign_id,
        campaign_version=1,
        planned_runs=tuple(planned),
        verifier_profile_hash=D2_VERIFIER_PROFILE_HASH,
        created_at=utc_now(),
    )
    plan = await ledger.plan_resume_with_receipts(
        manifest, task_run_ids=task_run_ids, campaign_id=partition.campaign_id
    )
    return {
        "planned": len(planned),
        "completed": len(plan.plan.completed),
        "remaining": len(plan.plan.remaining),
        "is_complete": plan.plan.is_complete,
        "is_resumable": plan.is_resumable,
        "refused": [str(item) for item in plan.refused],
        "actions": dict(Counter(item.action.value for item in plan.tasks)),
    }


async def _run(output: Path, model: Path, group_limit: int | None, resume_from: Path | None) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D2 writes only to its own pair")
    if artifact_root.name == "artifacts":
        raise SystemExit("refusing to run against the inconsistent development pair")

    tree_before = _git_state()
    engine = create_postgres_engine(database_url)
    started = utc_now()
    report: dict[str, object] = {
        "schema_version": 1,
        "sprint": "21D2",
        "wave": "W4",
        "items": ["S21D2-023", "S21D2-024", "S21D2-025"],
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
            verifier_profile_hash=D2_VERIFIER_PROFILE_HASH,
        )
        embed, model_digest = _embedding(model)

        report["store_before_campaign"] = {
            "correction_ranking_observations": len(
                await learned.list_observations(surface=CORRECTION_SURFACE, limit=500)
            ),
            "note": "prior executions in the isolated D2 pair; not deleted, subtracted",
        }

        bundle = seal_corpus()
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

        partitions = {name: _Partition(bundle.catalogues[name]) for name in _ORDER}
        bounds: NumericBounds | None = None
        with tempfile.TemporaryDirectory(prefix="cogos-d2-campaign-") as scratch:
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
                # Fitted on training and reused, never refitted per partition: bounds fitted
                # on calibration would carry calibration statistics into the encoder, which
                # is a leak no feature-name check would ever catch.
                if bounds is None:
                    bounds = NumericBounds.from_training(partition.rows)
                # W4-F3. On a resume the features must be the ones sealed before the
                # original execution, not a fresh seal: the replayed outcomes carry their
                # original times, and a seal stamped now would sit after them. The projector
                # refuses that, correctly — features that postdate their outcome are not
                # pre-outcome features. So the recorded seal time is reused, and the set has
                # to reproduce the recorded hash or the resume is describing a different
                # corpus and must not proceed.
                previously = sealed_before.get(name)
                sealed = seal_feature_records(
                    partition.pending,
                    partition=name.value,
                    campaign_manifest_hash=partition.catalogue.content_hash,
                    bounds=bounds,
                    embedding_model_id=minilm.MODEL_ID,
                    embedding_revision=model_digest,
                    embedding_dimension=minilm.DIMENSION,
                    sealed_at=utc_now() if previously is None else previously[0],
                )
                if previously is not None and sealed.content_hash != previously[1]:
                    raise SystemExit(
                        f"the {name.value} feature set no longer reproduces the seal it was "
                        f"executed under ({previously[1]} -> {sealed.content_hash}); the "
                        "corpus, the bounds or the embedding changed and this is a different "
                        "campaign wearing the same identity"
                    )
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
                partition.feature_set_hash = sealed.content_hash
                partition.feature_sealed_at = sealed.sealed_at

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
        report["resume"] = {
            name.value: await _resume_report(ledger, partitions[name]) for name in _ORDER
        }
        report["calibration_ood"] = await _resolve_calibration_ood(
            partitions[CorrectionPartition.CALIBRATION],
            artifacts=artifacts,
            submanifest_hash=bundle.calibration_ood.content_hash,
            seed=bundle.calibration_ood.perturbation_seed,
        )
        report["snapshot"] = await _snapshot(
            partitions,
            builder=builder,
            feature_schema_hash=CorrectionFeatureContract().content_hash,
        )
        report["group_disjointness"] = {
            "training_groups": len(bundle.groups_of(CorrectionPartition.TRAINING)),
            "calibration_groups": len(bundle.groups_of(CorrectionPartition.CALIBRATION)),
            "shared_with_calibration": sorted(
                bundle.groups_of(CorrectionPartition.TRAINING)
                & bundle.groups_of(CorrectionPartition.CALIBRATION)
            ),
            "calibration_groups_shared_with_final_a": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.FINAL_A)
            ),
            "calibration_groups_shared_with_final_b": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.FINAL_B)
            ),
            "calibration_groups_shared_with_canary": sorted(
                bundle.groups_of(CorrectionPartition.CALIBRATION)
                & bundle.groups_of(CorrectionPartition.CANARY)
            ),
            "inherited_groups_in_calibration": [
                group.repository_group
                for group in bundle.catalogues[CorrectionPartition.CALIBRATION].groups
                if group.inherited_from_d1
            ],
        }
        report["findings"] = FINDINGS
        report["deviations"] = DEVIATIONS
        report["provenance"] = {
            "real_governed_run_observations_written": 0,
            "final_batch_a_opened": False,
            "final_batch_b_opened": False,
            "canary_opened": False,
            "candidates_per_group": CANDIDATES_PER_GROUP,
        }
        report["storage"] = {
            "database": database_url.rsplit("/", 1)[-1],
            "artifact_root": str(artifact_root),
            "inconsistent_development_pair_writes": 0,
            "c3_or_d1_store_writes": 0,
        }
        report["embedding"] = {
            "model_id": minilm.MODEL_ID,
            "tree_digest": model_digest,
            "dimension": minilm.DIMENSION,
            "provider": "sentence_transformers, local frozen model, no network",
        }
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
    parser.add_argument(
        "--model", type=Path, required=True, help="the frozen local embedding model directory"
    )
    parser.add_argument(
        "--groups", type=int, help="run only the first N groups of each partition (smoke runs)"
    )
    parser.add_argument("--resume-from", type=Path)
    args = parser.parse_args()
    return asyncio.run(_run(args.output, args.model, args.groups, args.resume_from))


if __name__ == "__main__":
    raise SystemExit(main())
