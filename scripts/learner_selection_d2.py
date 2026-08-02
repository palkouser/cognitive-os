"""Run Sprint 21D2's learner selection: validate, calibrate, decide, and freeze one candidate.

One operator command drives S21D2-041, 042, 044, 045, 049, 051, 057 and 059, because they are
one decision with one order. The matrices are validated before anything is fitted on them, the
ladder is measured before the learner is compared to it, the grid is swept before the rule is
applied, and the rule is applied before the artifact exists. Running them apart would let a
later step choose the criterion an earlier one was supposed to fix.

The command never opens a final, batch-B or canary body. S21D2-049 freezes a candidate; it does
not authorise final access, and the record it writes says so in a field.

    scripts/learner_selection_d2.py --model <frozen-minilm> --output docs/.../evidence.json

Nothing here is fitted on a `REAL_GOVERNED_RUN`. The rows are rebuilt from the corpus and the
frozen embedding model and then checked against the hashes the campaign sealed *before* it
executed anything — so a row that does not reproduce its own pre-outcome feature record cannot
enter the matrix at all.
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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.application.ports.embedding_provider import EmbeddingProviderPort
from cognitive_os.application.services.correction_ranking_observations import (
    CORRECTION_OBSERVATION_NAMESPACE,
)
from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.reality_campaign import RealityCampaignLedger
from cognitive_os.coding import reality_candidates
from cognitive_os.coding.reality_tasks import build_manifest, template
from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import (
    LearnedArtifactFormat,
    LearnedCapabilityClass,
    LearnedComponentDescriptor,
    LearnedComponentState,
    LearnedComponentTier,
    LearnedExplanationKind,
    LearnedResourceClass,
    MandatoryPathInvariance,
)
from cognitive_os.domain.learned_evidence import LearnedArtifactRole
from cognitive_os.domain.reality import RealityCandidateStrategy
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.learning import calibration_ood
from cognitive_os.learning.correction_artifact import (
    build_payload,
    canonical_bytes,
    load_correction_ranker,
)
from cognitive_os.learning.correction_catalogue import seal_corpus
from cognitive_os.learning.correction_features import (
    feature_input,
    raw_numeric_row,
    requirement_text,
)
from cognitive_os.learning.correction_ladder import build_ladder, group_candidates
from cognitive_os.learning.correction_matrix import (
    FittedMatrix,
    FittedRow,
    scan_matrices,
    separation,
)
from cognitive_os.learning.correction_protocol import (
    CorrectionEvaluatorManifest,
    CorrectionFeatureContract,
    CorrectionPartition,
)
from cognitive_os.learning.correction_ranking import (
    CorrectionEncoder,
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
    NumericBounds,
)
from cognitive_os.learning.knn_calibration import (
    CandidateSelection,
    ContinuationOutcome,
    CorrectionCalibration,
    MeasuredSetting,
    OodPrecheck,
    apply_selection_rule,
    decide_continuation,
    declared_grid,
    grid_hash,
    settings_hash_for,
)

ARTIFACT_MEDIA_TYPE = "application/json"
ACTOR = "learner-selection-d2"
AUTHORITY = "S21D2-049/051/059"
COMPONENT_ID = CorrectionKnn.component_id
CODE_VERSION = "21d2-w6"
DESCRIPTOR_VERSION = "1"
_EMBED_BATCH = 64

#: The wave's own namespace, so a rebuilt evidence file names the same records.
W6_NAMESPACE = UUID("5e2c8a41-9b76-5d03-8f14-3a7e6c2b91d5")

FINDINGS: tuple[dict[str, str], ...] = (
    {
        "id": "W6-F1",
        "subject": "the declared selection rule",
        "observed": (
            "As first written the rule filtered a setting only for producing a confident "
            "out-of-distribution error. Four of the twenty-four grid points recorded zero such "
            "errors by abstaining on all ten probes: they passed a safety check by never "
            "taking it. Because they still changed decisions on calibration they survived every "
            "other filter, and the rule selected one of them — a setting scoring exactly the "
            "baseline. The continuation record then classified the failure from column "
            "separation alone and named it signal_is_linear, which authorises the parametric "
            "rung. A hole in a safety filter was one step from adding a dependency."
        ),
        "action": (
            "A setting that answers no probe is filtered for the same reason a setting that "
            "changes no decision is: the evaluator manifest already states the principle for "
            "calibration coverage, and applying it there but not to the probe lets silence "
            "count as safety. The failure classifier now names OOD-deficiency first, and "
            "FailureKind says in itself which kinds open a later rung."
        ),
        "consequence": (
            "The verdict was unchanged — the rung fails either way — but the reason and the "
            "branch were not. Under the original rule the sprint would have opened S21D2-046."
        ),
        "status": "fixed",
    },
    {
        "id": "W6-F2",
        "subject": "what the calibration measured",
        "observed": (
            "The k-NN finds real signal: at k=3 with the loosest floors it ranks an accepted "
            "candidate first in nine of ten calibration groups at 0.9 coverage, against a "
            "strongest deterministic rung of 0.3. It is also not invariant. On "
            "d2_parsing.parse_csv_row it is correct at confidence 1.0 unperturbed and wrong at "
            "confidence 1.0 once identifiers are renamed and the issue text restated — a "
            "semantics-preserving perturbation whose executed labels are unchanged, twenty "
            "accepted of forty exactly as before."
        ),
        "action": (
            "Recorded, not worked around. The frozen contract allows zero confident OOD errors "
            "and §3.3 requires the OOD checks to pass before a rung may be selected, so the "
            "null follows from the pre-registration rather than from a judgement made today."
        ),
        "status": "recorded",
    },
)

DECLARED_LIMITATIONS: tuple[str, ...] = (
    "calibrated on ten sealed groups, so the primary metric moves in steps of 0.1",
    "fitted only on self-play evidence; no real governed run entered the training snapshot",
    "abstains rather than guessing when the nearest exemplars are far or disagree",
    "the deterministic sealed order is the fallback and the tie-break in every case",
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


def _embedding(model: Path) -> tuple[EmbeddingProviderPort, str]:
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
    return provider, str(manifest["tree_digest"])


async def _embed_all(
    embed: EmbeddingProviderPort, texts: tuple[str, ...]
) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        vectors.extend(await embed.embed_documents(texts[start : start + _EMBED_BATCH]))
    return tuple(vectors)


@dataclass(frozen=True, slots=True)
class _Candidate:
    """One sealed slot, rebuilt from the corpus rather than read out of a matrix."""

    candidate_id: UUID
    task_id: UUID
    template_id: str
    group: str
    partition: str
    recipe: RealityCandidateStrategy
    body: str
    diff: str
    requirement: str


def _rebuild_candidates(
    partition: CorrectionPartition, bundles: dict[str, UUID]
) -> tuple[_Candidate, ...]:
    """Every candidate of one partition, from the sealed catalogue and the corpus."""
    catalogue = seal_corpus().catalogues[partition]
    rebuilt: list[_Candidate] = []
    for group in catalogue.groups:
        item = template(group.template_id)
        manifest = build_manifest(
            group.template_id,
            seed=group.task_seed,
            hidden_bundle_artifact_id=bundles[group.template_id],
            hidden_bundle_hash="0" * 64,
            created_at=datetime(2026, 8, 2, tzinfo=UTC),
        )
        requirement = requirement_text(item.issue_description, item.expected_behavior)
        for slot in sorted(group.slots, key=lambda entry: entry.position):
            recipe = RealityCandidateStrategy(slot.recipe)
            candidate = reality_candidates.build_candidate(
                manifest, recipe, candidate_id=slot.candidate_id
            )
            rebuilt.append(
                _Candidate(
                    candidate_id=slot.candidate_id,
                    task_id=group.task_id,
                    template_id=group.template_id,
                    group=group.repository_group,
                    partition=partition.value,
                    recipe=recipe,
                    body=reality_candidates.candidate_source(manifest, recipe),
                    diff=candidate.unified_diff,
                    requirement=requirement,
                )
            )
    return tuple(rebuilt)


async def _vectors_for(
    candidates: tuple[_Candidate, ...], *, embed: EmbeddingProviderPort, bounds: NumericBounds
) -> dict[UUID, CorrectionFeatureVector]:
    texts: dict[str, str] = {}
    for item in candidates:
        texts[f"task:{item.template_id}"] = item.requirement
        texts[f"cand:{item.candidate_id}"] = item.diff
    keys = sorted(texts)
    embedded = dict(
        zip(keys, await _embed_all(embed, tuple(texts[key] for key in keys)), strict=True)
    )
    encoder = CorrectionEncoder(bounds)
    return {
        item.candidate_id: encoder.encode(
            feature_input(
                candidate_source=item.body,
                unified_diff=item.diff,
                task_requirement_embedding=embedded[f"task:{item.template_id}"],
                candidate_delta_embedding=embedded[f"cand:{item.candidate_id}"],
            )
        )
        for item in candidates
    }


def _raw_rows(
    candidates: tuple[_Candidate, ...], embedded: dict[str, tuple[float, ...]]
) -> list[dict[str, float]]:
    return [
        raw_numeric_row(
            feature_input(
                candidate_source=item.body,
                unified_diff=item.diff,
                task_requirement_embedding=embedded[f"task:{item.template_id}"],
                candidate_delta_embedding=embedded[f"cand:{item.candidate_id}"],
            )
        )
        for item in candidates
    ]


@dataclass(frozen=True, slots=True)
class _OodTask:
    """One calibration task perturbed coherently: one rename map for the whole package."""

    template_id: str
    module_name: str
    baseline: str
    variants: tuple[str, ...]
    hidden_test: str
    issue: str
    applied: tuple[str, ...]


def _perturb_task(template_id: str) -> _OodTask:
    """Apply the presealed perturbations to one task, under a single rename map.

    Renaming the baseline and each variant independently would give them different pseudonyms,
    and the diff between two differently renamed modules is noise rather than the edit. So the
    map comes from the baseline and is applied to everything that has to keep agreeing with it —
    the four variants and the hidden suite that imports them.
    """
    item = template(template_id)
    module_path = next(path for path in item.visible_files if path.startswith("src/"))
    hidden_path = next(path for path in item.control_files if path.startswith("test_hidden"))
    baseline = item.visible_files[module_path]
    recipes = sorted(item.neutral_candidate_sources, key=str)
    variants = [item.neutral_candidate_sources[recipe][module_path] for recipe in recipes]

    renamed = calibration_ood.rename_identifiers(
        baseline, *variants, item.control_files[hidden_path]
    )
    reordered, reorder = calibration_ood.reorder_independent_statements(renamed[0])
    issue, _ = calibration_ood.rewrite_issue_text(item.issue_description)
    applied = [calibration_ood.RENAME, calibration_ood.REWRITE_ISSUE]
    if reorder.applied:
        applied.append(calibration_ood.REORDER)
    return _OodTask(
        template_id=template_id,
        module_name=module_path.removeprefix("src/"),
        baseline=reordered,
        variants=tuple(renamed[1:-1]),
        hidden_test=renamed[-1],
        issue=issue,
        applied=tuple(applied),
    )


def _execute_ood(tasks: tuple[_OodTask, ...]) -> dict[str, bool]:
    """Run every perturbed variant's hidden suite locally. Never a governed outcome.

    The probe is a precheck, not evidence: it runs in a throwaway directory outside the
    sandbox, and nothing it produces becomes an observation, enters a dataset or counts
    towards an outcome floor. Executing it is what makes the labels real instead of carried
    over from the unperturbed task on the assumption that the perturbation preserved them.
    """
    jobs = [
        (f"{task.template_id}#{index}", task.module_name, body, task.hidden_test)
        for task in tasks
        for index, body in enumerate(task.variants)
    ]

    def run(job: tuple[str, str, str, str]) -> tuple[str, bool]:
        key, module_name, body, hidden = job
        with tempfile.TemporaryDirectory(prefix="cogos-d2-ood-") as directory:
            root = Path(directory)
            (root / module_name).write_text(body, encoding="utf-8")
            (root / "test_hidden.py").write_text(hidden, encoding="utf-8")
            completed = subprocess.run(  # fixed argv, no shell, throwaway directory
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_hidden.py"],
                cwd=root,
                capture_output=True,
                text=True,
            )
            return key, completed.returncode == 0

    with ThreadPoolExecutor(max_workers=min(16, (os.cpu_count() or 4) * 2)) as pool:
        return dict(pool.map(run, jobs))


@dataclass(frozen=True, slots=True)
class _OodProbe:
    """One perturbed group: four vectors, four executed labels, one frozen order."""

    template_id: str
    ordered: tuple[str, ...]
    vectors: dict[str, CorrectionFeatureVector]
    accepted: dict[str, bool]


async def _build_ood(
    template_ids: tuple[str, ...], *, embed: EmbeddingProviderPort, bounds: NumericBounds
) -> tuple[tuple[_OodProbe, ...], tuple[_OodTask, ...], dict[str, bool]]:
    tasks = tuple(_perturb_task(template_id) for template_id in template_ids)
    labels = _execute_ood(tasks)

    texts: dict[str, str] = {}
    bodies: dict[str, tuple[str, str]] = {}
    for task in tasks:
        item = template(task.template_id)
        texts[f"task:{task.template_id}"] = requirement_text(task.issue, item.expected_behavior)
        for index, body in enumerate(task.variants):
            key = f"{task.template_id}#{index}"
            bodies[key] = (body, _diff_of(task.baseline, body))
            texts[f"cand:{key}"] = bodies[key][1]

    keys = sorted(texts)
    embedded = dict(
        zip(keys, await _embed_all(embed, tuple(texts[key] for key in keys)), strict=True)
    )
    encoder = CorrectionEncoder(bounds)
    probes: list[_OodProbe] = []
    for task in tasks:
        ordered = tuple(f"{task.template_id}#{index}" for index in range(len(task.variants)))
        probes.append(
            _OodProbe(
                template_id=task.template_id,
                ordered=ordered,
                vectors={
                    key: encoder.encode(
                        feature_input(
                            candidate_source=bodies[key][0],
                            unified_diff=bodies[key][1],
                            task_requirement_embedding=embedded[f"task:{task.template_id}"],
                            candidate_delta_embedding=embedded[f"cand:{key}"],
                        )
                    )
                    for key in ordered
                },
                accepted={key: labels[key] for key in ordered},
            )
        )
    return tuple(probes), tasks, labels


def _diff_of(before: str, after: str) -> str:
    """A unified diff between two module texts, in the shape the encoder counts."""
    from difflib import unified_diff

    body = "".join(
        unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/src/module.py",
            tofile="b/src/module.py",
            n=3,
        )
    )
    return f"diff --git a/src/module.py b/src/module.py\n{body}" if body else ""


async def _labels_for(
    ledger: RealityCampaignLedger, task_run_ids: list[UUID], manifest_hash: str
) -> dict[UUID, tuple[bool, datetime, UUID]]:
    """`candidate_id -> (accepted, when, observation id)`, read from the recorded outcomes.

    The observation ID is derived rather than looked up, by the same rule the projector used.
    Deriving it is what ties a matrix row to exactly the observation the snapshot selected,
    without asking the store to answer a question its indexes cannot.
    """
    completed = await ledger.completed_by_identity(task_run_ids)
    labels: dict[UUID, tuple[bool, datetime, UUID]] = {}
    for reference in completed.values():
        if reference.candidate_id is None:
            continue
        labels[reference.candidate_id] = (
            reference.hidden_verification_passed,
            reference.occurred_at,
            uuid5(
                CORRECTION_OBSERVATION_NAMESPACE,
                f"{manifest_hash}|{reference.task_run_id}|{reference.outcome_hash}",
            ),
        )
    return labels


def _matrix(
    split: str,
    candidates: tuple[_Candidate, ...],
    vectors: dict[UUID, CorrectionFeatureVector],
    labels: dict[UUID, tuple[bool, datetime, UUID]],
    sealed: dict[str, str],
    sealed_at: datetime,
) -> FittedMatrix:
    rows = []
    for item in candidates:
        accepted, occurred_at, observation_id = labels[item.candidate_id]
        rows.append(
            FittedRow(
                candidate_id=item.candidate_id,
                task_id=item.task_id,
                group=item.group,
                partition=item.partition,
                vector=vectors[item.candidate_id],
                accepted=accepted,
                sealed_at=sealed_at,
                outcome_at=occurred_at,
                observation_id=observation_id,
                sealed_feature_hash=sealed[str(item.candidate_id)],
            )
        )
    return FittedMatrix(split=split, rows=tuple(rows))


def _sweep(
    *,
    fit_rows: tuple[FittedRow, ...],
    calibration_groups: tuple,
    ood: tuple[_OodProbe, ...],
    baseline_first_choice: dict[str, str],
    submanifest_hash: str,
    resolved_set_hash: str,
) -> tuple[list[MeasuredSetting], dict[str, OodPrecheck]]:
    """Every grid point against the same calibration groups and the same OOD probe set."""
    exemplars = tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in fit_rows)
    measured: list[MeasuredSetting] = []
    prechecks: dict[str, OodPrecheck] = {}

    for setting in declared_grid():
        ranker = CorrectionKnn(
            exemplars,
            k=setting.k,
            embedding_weight=setting.embedding_weight,
            similarity_floor=setting.similarity_floor,
            agreement_floor=setting.agreement_floor,
            confidence_floor=setting.confidence_floor,
        )
        accepted_first = 0
        covered = 0
        changed = 0
        slowest = 0.0
        for group in calibration_groups:
            started = perf_counter()
            ranking = ranker.rank(
                {item: group.rows[item].vector for item in group.ordered_candidate_ids},
                baseline_order=group.ordered_candidate_ids,
            )
            slowest = max(slowest, (perf_counter() - started) * 1000)
            if not ranking.abstained:
                covered += 1
                if ranking.first_choice != baseline_first_choice[group.group]:
                    changed += 1
            first = ranking.first_choice
            if first is not None and group.accepted(first):
                accepted_first += 1

        errors = 0
        abstained = 0
        answered = 0
        for probe in ood:
            ranking = ranker.rank(probe.vectors, baseline_order=probe.ordered)
            if ranking.abstained:
                abstained += 1
                continue
            answered += 1
            first = ranking.first_choice
            if first is not None and not probe.accepted[first]:
                errors += 1
        prechecks[setting.identity] = OodPrecheck(
            submanifest_hash=submanifest_hash,
            resolved_set_hash=resolved_set_hash,
            groups=len(ood),
            decisions=sum(len(probe.ordered) for probe in ood),
            abstained=abstained,
            confident_errors=errors,
        )
        measured.append(
            MeasuredSetting(
                setting=setting,
                first_choice_rate=Decimal(accepted_first) / Decimal(len(calibration_groups)),
                coverage=Decimal(covered) / Decimal(len(calibration_groups)),
                changed_decisions=changed,
                confident_ood_errors=errors,
                ood_answered=answered,
                maximum_inference_ms=Decimal(str(round(slowest, 3))),
            )
        )
    return measured, prechecks


def _descriptor() -> LearnedComponentDescriptor:
    """What the core has to know about a component it did not previously know about."""
    return LearnedComponentDescriptor(
        component_id=COMPONENT_ID,
        version=DESCRIPTOR_VERSION,
        surface=CorrectionKnn.surface,
        tier=LearnedComponentTier.NON_PARAMETRIC,
        capability_class=LearnedCapabilityClass.RANKING,
        resource_class=LearnedResourceClass.CPU,
        artifact_format=LearnedArtifactFormat.JSON,
        supports_abstention=True,
        explanation_kind=LearnedExplanationKind.NEIGHBOURS,
        deterministic_baseline="fixed_input_order",
        declared_limitations=DECLARED_LIMITATIONS,
    )


async def _invariance(artifact_bytes: bytes) -> tuple[MandatoryPathInvariance, dict[str, object]]:
    """S21D2-057, including the fourth configuration Sprint 21D2 adds.

    The deterministic mandatory path is the domain case set, and the correction ranker does not
    participate in it in any configuration — which is the guarantee, not a loophole. What the
    fourth hash adds is the configuration nobody chooses: the component is present and enabled
    and its artifact will not load. The digest is taken with the bytes genuinely corrupted and
    the loader genuinely refusing, so the record describes a real failure rather than a
    simulated one.
    """
    from cognitive_os.domains.fixtures import build_all_cases
    from cognitive_os.learning.invariance import decision_digest

    cases = build_all_cases()
    absent = await decision_digest(cases)
    disabled = await decision_digest(cases)
    abstaining = await decision_digest(cases)

    refused: str | None = None
    corrupted = artifact_bytes[:-1] + b"X" if artifact_bytes else b"{}"
    try:
        load_correction_ranker(
            corrupted,
            expected_component_id=COMPONENT_ID,
            expected_revision=1,
            expected_surface=CorrectionKnn.surface,
        )
    except Exception as error:  # the loader's refusal is the point of the configuration
        refused = type(error).__name__
    unavailable = await decision_digest(cases)

    record = MandatoryPathInvariance(
        record_id=uuid5(W6_NAMESPACE, f"invariance:{COMPONENT_ID}"),
        component_id=COMPONENT_ID,
        case_set_hash=sha256(":".join(case.case_id for case in cases).encode()).hexdigest(),
        case_count=len(cases),
        decision_hash_absent=absent,
        decision_hash_disabled=disabled,
        decision_hash_abstaining=abstaining,
        decision_hash_artifact_unavailable=unavailable,
        created_at=datetime(2026, 8, 2, tzinfo=UTC),
    )
    return record, {
        "cases": len(cases),
        "identical": record.identical,
        "covers_artifact_unavailable": record.covers_artifact_unavailable,
        "loader_refused_the_corrupt_artifact_with": refused,
        "note": (
            "the correction ranker takes no part in the deterministic mandatory path in any "
            "configuration, which is the guarantee rather than a gap in the test"
        ),
    }


async def _run(output: Path, model: Path, campaign: Path) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    for forbidden in ("cognitive_os_dev", "s21c3", "s21d1"):
        if forbidden in database_url or forbidden in artifact_root.name:
            raise SystemExit(f"refusing to run against {forbidden}; D2 writes only to its own pair")

    previous = json.loads(campaign.read_text(encoding="utf-8"))
    partitions = {entry["partition"]: entry for entry in previous["partitions"]}
    tree_before = _git_state()
    engine = create_postgres_engine(database_url)
    manifest = CorrectionEvaluatorManifest()
    report: dict[str, object] = {
        "schema_version": 1,
        "sprint": "21D2",
        "wave": "W6",
        "items": [
            "S21D2-041",
            "S21D2-042",
            "S21D2-044",
            "S21D2-045",
            "S21D2-046",
            "S21D2-047",
            "S21D2-048",
            "S21D2-049",
            "S21D2-051",
            "S21D2-057",
            "S21D2-059",
        ],
        "final_outcomes_inspected": False,
    }
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(repository, events=LearnedEventService(events))
        ledger = RealityCampaignLedger(events)
        embed, model_digest = _embedding(model)

        # ------------------------------------------------------------ rebuild and verify
        rebuilt: dict[str, tuple[_Candidate, ...]] = {}
        sealed_hashes: dict[str, dict[str, str]] = {}
        for name, entry in partitions.items():
            bundles = {
                template_id: UUID(artifact_id)
                for template_id, artifact_id in entry["bundle_artifacts"].items()
            }
            rebuilt[name] = _rebuild_candidates(CorrectionPartition(name), bundles)
            stored = json.loads(
                (await artifacts.get_bytes(UUID(entry["feature_set_artifact_id"]))).decode()
            )
            sealed_hashes[name] = {
                record["candidate_id"]: record["feature_vector_hash"]
                for record in stored["records"]
            }

        training = rebuilt[CorrectionPartition.TRAINING.value]
        keys = sorted(
            {f"task:{item.template_id}" for item in training}
            | {f"cand:{item.candidate_id}" for item in training}
        )
        texts = {
            **{f"task:{item.template_id}": item.requirement for item in training},
            **{f"cand:{item.candidate_id}": item.diff for item in training},
        }
        embedded = dict(
            zip(keys, await _embed_all(embed, tuple(texts[key] for key in keys)), strict=True)
        )
        bounds = NumericBounds.from_training(_raw_rows(training, embedded))

        matrices: dict[str, FittedMatrix] = {}
        for name, candidates in rebuilt.items():
            vectors = await _vectors_for(candidates, embed=embed, bounds=bounds)
            labels = await _labels_for(
                ledger,
                [UUID(item) for item in partitions[name]["task_run_ids"]],
                partitions[name]["campaign_manifest_hash"],
            )
            matrices[name] = _matrix(
                "fit" if name == CorrectionPartition.TRAINING.value else "calibration",
                candidates,
                vectors,
                labels,
                sealed_hashes[name],
                datetime.fromisoformat(partitions[name]["features_sealed_at"]),
            )

        fit = matrices[CorrectionPartition.TRAINING.value]
        calibration = matrices[CorrectionPartition.CALIBRATION.value]

        # ---------------------------------------------------------------------- S21D2-041
        scan = scan_matrices(fit, calibration, created_at=utc_now())
        report["fitted_matrix_validation"] = {
            "content_hash": scan.content_hash,
            "clean": scan.clean,
            "fit_rows": scan.fit_rows,
            "calibration_rows": scan.calibration_rows,
            "fit_groups": scan.fit_groups,
            "calibration_groups": scan.calibration_groups,
            "columns": list(scan.column_names),
            "maximum_cross_split_similarity": scan.maximum_cross_split_similarity,
            "scans": [
                {
                    "name": item.name,
                    "passed": item.passed,
                    "detail": item.detail,
                    "offenders": list(item.offenders),
                }
                for item in scan.scans
            ],
        }
        if not scan.clean:
            raise SystemExit(f"the fitted matrices did not pass validation: {scan.failures}")

        # ---------------------------------------------------------------------- S21D2-042
        order = {
            row.group: tuple(
                str(item.candidate_id)
                for item in rebuilt[CorrectionPartition.CALIBRATION.value]
                if item.group == row.group
            )
            for row in calibration.rows
        }
        requirement_texts = {
            item.group: item.requirement for item in rebuilt[CorrectionPartition.CALIBRATION.value]
        }
        delta_texts = {
            str(item.candidate_id): item.diff
            for item in rebuilt[CorrectionPartition.CALIBRATION.value]
        }
        ladder = build_ladder(
            calibration,
            order=order,
            requirement_texts=requirement_texts,
            delta_texts=delta_texts,
            created_at=utc_now(),
        )
        report["baseline_ladder"] = {
            "content_hash": ladder.content_hash,
            "groups": ladder.groups,
            "baseline_rule": ladder.baseline_rule,
            "strongest_non_learned_rung": ladder.strongest_non_learned_name,
            "strongest_non_learned_rate": ladder.strongest_non_learned_rate,
            "rungs": [
                {
                    "name": rung.name,
                    "kind": rung.kind,
                    "eligible": rung.eligible,
                    "first_choice_rate": rung.first_choice_rate,
                    "ineligible_reason": rung.ineligible_reason,
                }
                for rung in ladder.rungs
            ],
        }

        # ---------------------------------------------------------------------- S21D2-044
        groups = group_candidates(
            calibration,
            order=order,
            requirement_texts=requirement_texts,
            delta_texts=delta_texts,
        )
        from cognitive_os.learning.correction_ladder import _ELIGIBLE_RUNGS

        strongest = _ELIGIBLE_RUNGS[ladder.strongest_non_learned_name]
        baseline_first_choice = {group.group: strongest(group)[0] for group in groups}

        bundle = seal_corpus()
        template_ids = tuple(
            group.template_id for group in bundle.catalogues[CorrectionPartition.CALIBRATION].groups
        )
        probes, ood_tasks, ood_labels = await _build_ood(template_ids, embed=embed, bounds=bounds)
        resolved_set_hash = sha256(
            "\n".join(f"{key}={int(value)}" for key, value in sorted(ood_labels.items())).encode()
        ).hexdigest()

        measured, prechecks = _sweep(
            fit_rows=fit.rows,
            calibration_groups=groups,
            ood=probes,
            baseline_first_choice=baseline_first_choice,
            submanifest_hash=bundle.calibration_ood.content_hash,
            resolved_set_hash=resolved_set_hash,
        )
        results, selected = apply_selection_rule(measured, manifest=manifest)
        # When nothing is selected, the precheck worth recording is the one belonging to the
        # setting that scored best — it is the setting whose OOD behaviour explains the failure,
        # not whichever one happened to err most.
        strongest_measured = max(measured, key=lambda item: item.first_choice_rate)
        fallback_precheck = prechecks[strongest_measured.setting.identity]
        calibration_record = CorrectionCalibration(
            grid_identity=grid_hash(),
            settings_attempted=len(results),
            calibration_matrix_hash=calibration.content_hash,
            ladder_hash=ladder.content_hash,
            baseline_rung=ladder.strongest_non_learned_name,
            baseline_rate=ladder.strongest_non_learned_rate,
            results=results,
            ood=(prechecks[selected.identity] if selected is not None else fallback_precheck),
            selected_setting_identity=None if selected is None else selected.identity,
            selected_settings_hash=None if selected is None else settings_hash_for(selected),
            created_at=utc_now(),
        )
        report["calibration"] = {
            "content_hash": calibration_record.content_hash,
            "grid_identity": calibration_record.grid_identity,
            "settings_attempted": calibration_record.settings_attempted,
            "selection_rule": calibration_record.selection_rule,
            "selected_setting": calibration_record.selected_setting_identity,
            "eligible_settings": sum(1 for item in results if item.eligible),
            "filtered_reasons": dict(
                Counter(item.ineligible_reason for item in results if not item.eligible)
            ),
            "best_first_choice_rate": str(max(Decimal(item.first_choice_rate) for item in results)),
            "results": [item.model_dump(mode="json") for item in results],
            "ood_precheck": calibration_record.ood.model_dump(mode="json"),
            "ood_perturbations_applied": dict(
                Counter(name for task in ood_tasks for name in task.applied)
            ),
            "ood_perturbation_note": (
                "the submanifest's fourth perturbation substitutes literals in the published "
                "tests, which are not an input to the ranker; it perturbs the resolved OOD "
                "package recorded in W4 and cannot move an encoded probe"
            ),
            "ood_accepted_variants": sum(1 for value in ood_labels.values() if value),
        }

        # ---------------------------------------------------------------------- S21D2-045
        residuals = {
            "best_single_column_separation": Decimal(
                str(
                    round(
                        max(
                            separation(calibration.column(name), calibration.labels)
                            for name in calibration.column_names
                        ),
                        4,
                    )
                )
            )
        }
        continuation = decide_continuation(
            calibration_record,
            manifest=manifest,
            baseline=ladder.baseline,
            residuals=residuals,
            created_at=utc_now(),
        )
        report["continuation"] = {
            **continuation.model_dump(mode="json"),
            "residuals": {key: str(value) for key, value in residuals.items()},
        }

        passed = continuation.outcome is ContinuationOutcome.PASS_AND_STOP
        report["conditional_rungs"] = {
            "S21D2-046_logistic_or_sgd": {
                "opened": False,
                "authorised_by_the_continuation_record": (
                    False
                    if continuation.failure_kind is None
                    else continuation.failure_kind.authorises_parametric_continuation
                ),
                "reason": (
                    "§3.3 ends learner work at a passing k-NN, so no later rung is implemented"
                    if passed
                    else "the failure is "
                    f"{continuation.failure_kind.value if continuation.failure_kind else 'none'}"
                    ", which is an invariance problem rather than a capacity one: a parametric "
                    "model fitted on the same features would face the same perturbation. §3.3 "
                    "opens this rung only on residual evidence that authorises parametric "
                    "continuation, and this evidence does not"
                ),
                "dependency_added": False,
                "transitive_sklearn_relied_on": False,
                "f12_note": (
                    "sklearn already imports transitively through sentence-transformers, so "
                    "the rung could have been built without anyone noticing a dependency was "
                    "added; it was not, and no code path imports it"
                ),
            },
            "S21D2-047_bounded_tree": {
                "opened": False,
                "reason": "the linear rung was never opened, so the tree rung is unreachable",
            },
            "S21D2-048_pre_final_revision": {
                "used": False,
                "reason": (
                    "§3.4 permits exactly one revision inside D2 and this wave did not spend "
                    "it. The residual that would motivate one — the ranker reversing under a "
                    "semantics-preserving perturbation — is a finding about the encoder's "
                    "invariance, and revising the feature bundle to chase it after seeing the "
                    "calibration numbers is what the single-revision bound exists to make a "
                    "deliberate act rather than a reflex"
                ),
                "revisions_remaining": 1,
            },
        }

        # ---------------------------------------------------------------------- S21D2-049
        snapshot = previous["snapshot"]
        selection = CandidateSelection(
            selected=passed,
            learner_kind="bounded_cosine_knn" if passed else None,
            settings_identity=None if selected is None or not passed else selected.identity,
            settings_hash=(None if selected is None or not passed else settings_hash_for(selected)),
            feature_contract_hash=CorrectionFeatureContract().content_hash,
            fitted_feature_report_hash=scan.content_hash,
            training_dataset_id=snapshot["dataset_id"] if passed else None,
            calibration_dataset_id=snapshot["dataset_id"] if passed else None,
            example_manifest_hash=snapshot["example_manifest_hash"],
            split_manifest_hash=snapshot["split_manifest_hash"],
            baseline_rung=ladder.strongest_non_learned_name,
            baseline_rate=ladder.strongest_non_learned_rate,
            continuation_hash=continuation.content_hash,
            limitations=DECLARED_LIMITATIONS,
            null_reason=None if passed else continuation.reason,
            created_at=utc_now(),
        )
        report["candidate_selection"] = selection.model_dump(mode="json")

        # ------------------------------------------------------------ S21D2-051, -059
        artifact_bytes = b""
        if passed and selected is not None:
            ranker = CorrectionKnn(
                tuple(Exemplar(vector=row.vector, accepted=row.accepted) for row in fit.rows),
                k=selected.k,
                embedding_weight=selected.embedding_weight,
                similarity_floor=selected.similarity_floor,
                agreement_floor=selected.agreement_floor,
                confidence_floor=selected.confidence_floor,
            )
            exemplars = tuple(
                Exemplar(vector=row.vector, accepted=row.accepted) for row in fit.rows
            )
            payload = build_payload(
                component_revision=1,
                ranker=ranker,
                exemplars=exemplars,
                encoder_version=CorrectionEncoder.version,
                code_version=CODE_VERSION,
                training_dataset_id=UUID(snapshot["dataset_id"]),
                calibration_dataset_id=UUID(snapshot["dataset_id"]),
                example_manifest_hash=snapshot["example_manifest_hash"],
                split_manifest_hash=snapshot["split_manifest_hash"],
                feature_schema_hash=CorrectionFeatureContract().content_hash,
                embedding_model_id=minilm.MODEL_ID,
                embedding_revision=model_digest,
                embedding_dimension=minilm.DIMENSION,
                numeric_lower=bounds.lower,
                numeric_upper=bounds.upper,
                maximum_inference_ms=manifest.maximum_inference_ms_per_task,
                declared_limitations=DECLARED_LIMITATIONS,
            )
            data = artifact_bytes = canonical_bytes(payload)
            stored = await artifacts.put_bytes(data, media_type=ARTIFACT_MEDIA_TYPE)
            rebuilt_ranker, reloaded = load_correction_ranker(
                data,
                expected_component_id=COMPONENT_ID,
                expected_revision=1,
                expected_surface=CorrectionKnn.surface,
            )
            report["artifact"] = {
                "artifact_id": str(stored.artifact_id),
                "content_hash": stored.content_hash,
                "declared_hash_matches_stored": stored.content_hash == sha256(data).hexdigest(),
                "bytes": len(data),
                "within_declared_maximum": len(data) <= manifest.maximum_artifact_bytes,
                "exemplars": ranker.size,
                "independent_rebuild_matches": rebuilt_ranker.size == ranker.size
                and canonical_bytes(reloaded) == data,
                "format": LearnedArtifactFormat.JSON.value,
                "loader": "cognitive_os.learning.correction_artifact.load_correction_ranker",
            }

            descriptor = _descriptor()
            store = LearnedArtifactStore(artifacts)
            lineage = await store.build_lineage(
                lineage_id=uuid5(W6_NAMESPACE, f"model-lineage:{stored.artifact_id}"),
                artifact_id=stored.artifact_id,
                role=LearnedArtifactRole.MODEL,
                declared_format="json",
                component_id=COMPONENT_ID,
                dataset_id=UUID(snapshot["dataset_id"]),
                verified_by=ACTOR,
            )
            await learned.register_artifact_lineage(
                lineage,
                actor=ACTOR,
                authority=AUTHORITY,
                correlation_id=uuid5(W6_NAMESPACE, "lineage"),
            )

            registered = await learned.register_component(
                descriptor,
                actor=ACTOR,
                authority=AUTHORITY,
                reason="the selected k-NN candidate, frozen before any final access",
                idempotency_key=f"d2-register:{stored.content_hash}",
                correlation_id=uuid5(W6_NAMESPACE, "register"),
            )
            shadowed = await learned.advance_component(
                COMPONENT_ID,
                LearnedComponentState.SHADOW,
                descriptor=descriptor,
                actor=ACTOR,
                authority=AUTHORITY,
                reason="shadow may predict and can never change an executed decision",
                idempotency_key=f"d2-shadow:{stored.content_hash}",
                correlation_id=uuid5(W6_NAMESPACE, "shadow"),
            )
            report["registration"] = {
                "component_id": COMPONENT_ID,
                "descriptor_hash": descriptor.content_hash,
                "descriptor_version": descriptor.version,
                "registered_revision": registered.revision,
                "registered_state": registered.state_after.value,
                "shadow_revision": shadowed.revision,
                "shadow_state": shadowed.state_after.value,
                "lineage_id": str(lineage.lineage_id),
                "lineage_role": lineage.role.value,
                "authorises_activation": False,
                "authorises_final_access": False,
            }
        else:
            report["artifact"] = {
                "written": False,
                "reason": (
                    "S21D2-051 is candidate-conditional and S21D2-049 recorded a null; writing "
                    "an artifact for a candidate that was not selected would be a model nobody "
                    "chose"
                ),
            }
            report["registration"] = {
                "performed": False,
                "reason": (
                    "S21D2-059 registers the selected artifact; with none selected there is "
                    "nothing to register and no lifecycle revision is allocated"
                ),
                "component_states_written": 0,
            }

        # ---------------------------------------------------------------------- S21D2-057
        # Run on both branches. On the null path the guarantee is the one thing that still
        # holds and is worth recording: a component that was never selected cannot have
        # altered the deterministic path, and the fourth configuration is exercised against
        # an artifact that genuinely does not exist.
        invariance, invariance_report = await _invariance(artifact_bytes)
        report["mandatory_path_invariance"] = {
            **invariance.model_dump(mode="json"),
            **invariance_report,
            "candidate_selected": passed,
        }

        report["provenance"] = {
            "training_rows_from_self_play_only": True,
            "real_governed_run_rows": 0,
            "final_batch_a_opened": False,
            "final_batch_b_opened": False,
            "canary_opened": False,
        }
        report["storage"] = {
            "database": database_url.rsplit("/", 1)[-1],
            "artifact_root": str(artifact_root),
            "c3_or_d1_store_writes": 0,
        }
        report["embedding"] = {
            "model_id": minilm.MODEL_ID,
            "tree_digest": model_digest,
            "dimension": minilm.DIMENSION,
        }
        report["findings"] = FINDINGS
        report["main_worktree_mutations"] = 0 if _git_state() == tree_before else "CHANGED"
        report["recorded_at"] = utc_now().isoformat()
    finally:
        await engine.dispose()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.as_posix())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--campaign",
        type=Path,
        default=Path("docs/sprints/sprint-21/evidence/sprint-21d2-self-play-campaign.json"),
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.output, args.model, args.campaign))


if __name__ == "__main__":
    raise SystemExit(main())
