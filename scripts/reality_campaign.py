"""Run the Sprint 21C3 offline reality campaign end to end and publish its statistics.

One operator command drives S21C3-031, 034, 035, 036 and 037, because they are one pipeline:
runs produce outcomes, outcomes produce trajectories, trajectories produce corpus items, and
every count in the report is read back out of what was persisted rather than accumulated in
this process. A statistics file built from in-memory counters would be a report about the
script; this one can be recomputed from the C3 database and Artifact Store alone.

Storage is the isolated C3 pair from S21C3-003 (`COGOS_DATABASE_URL` and
`COGOS_ARTIFACT_ROOT`, normally from `.env.s21c3.local`). The inconsistent development pair
is never opened.

    scripts/reality_campaign.py --output docs/sprints/sprint-21/evidence/... [--tasks N]

Resume is safe and is the default: `RealityCampaignLedger` reconstructs which run identities
already have a recorded outcome from the Event Store, and those are skipped. Re-running the
whole command after a crash therefore costs containers, not duplicate outcomes.
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
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4, uuid5

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.application.services.experience_compiler import (
    ExperienceCompilerService,
)
from cognitive_os.application.services.learned_datasets import (
    LearnedDatasetBuilder,
)
from cognitive_os.application.services.learned_evidence import (
    LearnedEvidenceService,
)
from cognitive_os.application.services.learned_intake import (
    LearnedObservationIntake,
)
from cognitive_os.application.services.reality_campaign import (
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_campaign_runner import (
    RealityCampaignRunner,
    TaskRuns,
)
from cognitive_os.application.services.reality_outcome_harvester import (
    CODING_REPAIR_SURFACE,
    RealityOutcomeHarvester,
)
from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.context_adapter import context_benchmark_case
from cognitive_os.benchmarks.domain_adapter import domain_benchmark_case
from cognitive_os.benchmarks.experience_adapter import experience_benchmark_case
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.benchmarks.semantic_adapter import semantic_benchmark_case
from cognitive_os.benchmarks.skill_adapter import skill_benchmark_case
from cognitive_os.benchmarks.strategy_adapter import strategy_benchmark_case
from cognitive_os.coding import reality_corpus_items, reality_trajectories
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import (
    available_templates,
    offline_strategies,
)
from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.errors import CorpusConflictError
from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import CorpusRole, ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedRepositoryError,
    ObservationAttribution,
    ObservationStatus,
)
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityOutcomeReference,
    RealityRunIdentity,
)
from cognitive_os.domain.sandbox import SandboxLimits
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.infrastructure.artifacts.filesystem import (
    ContentAddressedFilesystem,
)
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.corpus.postgres.repository import (
    PostgresCorpusRepository,
)
from cognitive_os.infrastructure.experience.postgres.repository import (
    PostgresExperienceRepository,
)
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.postgres.artifact_repository import (
    PostgresArtifactRepository,
)
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

CAMPAIGN_NAMESPACE = UUID("b3f7d914-6a28-5e40-9c15-7d2e8b46f0a3")

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

#: The C3 verifier profile every run in this campaign was measured against. Recorded in each
#: run identity so a resumed campaign cannot silently mix two verifier revisions.
VERIFIER_PROFILE_HASH = uuid5(CAMPAIGN_NAMESPACE, "coding.hidden_pytest:v1").hex * 2

FEATURE_SCHEMA_HASH = uuid5(CAMPAIGN_NAMESPACE, "c3-evaluation-features:v1").hex * 2

#: Task generation is a pure function of the template, the seed and this constant. Reading a
#: clock here would give the same task a new manifest hash on every run, and the manifest hash
#: is what a resumed campaign matches outcomes against and what the corpus plane deduplicates.
GENERATION_EPOCH = datetime(2026, 7, 30, tzinfo=UTC)

#: The governed cases replayed for S21C3-033, and the adapter that actually executes each.
#: Six subsystems across eight benchmark domains, all credential-free and deterministic.
_BENCHMARK_EXECUTORS = {
    "benchmarks/manifests/sprint20-domain-ci.yaml": domain_benchmark_case,
    "benchmarks/manifests/sprint14-experience-ci.yaml": experience_benchmark_case,
    "benchmarks/manifests/sprint13-strategies-ci.yaml": strategy_benchmark_case,
    "benchmarks/manifests/sprint12-skill-ci.yaml": skill_benchmark_case,
    "benchmarks/manifests/sprint11-context-ci.yaml": context_benchmark_case,
    "benchmarks/manifests/sprint10-semantic-ci.yaml": semantic_benchmark_case,
}


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"{name} is required. Source the isolated C3 environment first:\n"
            f"    set -a && . ./.env.s21c3.local && set +a"
        )
    return value


def _git_state() -> str:
    """The working tree as git sees it. Compared before and after the campaign."""
    return subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


async def _completed_runs(
    ledger: RealityCampaignLedger, resume_from: Path | None
) -> tuple[dict[str, RealityOutcomeReference], dict[str, UUID]]:
    """Outcomes the Event Store already holds, keyed by run identity, plus their bundles.

    The task-run IDs come from a previous run's evidence file because the Event Store is
    keyed by stream and there is no index from campaign to stream — `RealityCampaignLedger`
    says so in its own docstring, and inventing one here would mean a second ledger. Without
    `--resume-from` the campaign starts clean, which is the safe default: it costs containers,
    never correctness.
    """
    if resume_from is None:
        return {}, {}
    previous = json.loads(resume_from.read_text(encoding="utf-8"))
    completed = await ledger.completed_by_identity(
        UUID(item) for item in previous["execution"]["task_run_ids"]
    )
    bundles = {
        template_id: UUID(artifact_id)
        for template_id, artifact_id in previous["execution"]["bundle_artifacts"].items()
    }
    return completed, bundles


async def _run(output: Path, task_limit: int | None, resume_from: Path | None) -> int:
    database_url = _require("COGOS_DATABASE_URL")
    artifact_root = Path(_require("COGOS_ARTIFACT_ROOT"))
    if "cognitive_os_dev" in database_url or artifact_root.name == "artifacts":
        raise SystemExit(
            "refusing to run against the inconsistent development pair; §1.4 forbids C3 writes"
        )

    tree_before = _git_state()
    engine = create_postgres_engine(database_url)
    started = utc_now()
    report: dict[str, object] = {"schema_version": 1, "sprint": "21C3", "wave": "W3"}
    try:
        artifacts = ArtifactService(
            ContentAddressedFilesystem(artifact_root), PostgresArtifactRepository(engine)
        )
        events = PostgresEventStore(engine, build_default_event_catalog())
        recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)
        learned_repository = PostgresLearnedEvidenceRepository(engine)
        learned = LearnedEvidenceService(learned_repository, events=LearnedEventService(events))
        intake = LearnedObservationIntake(learned)
        harvester = RealityOutcomeHarvester(artifacts, events, intake)
        ledger = RealityCampaignLedger(events)
        sandbox = DockerSandbox(SANDBOX_IMAGE)
        runner = RealityCampaignRunner(
            sandbox=sandbox,
            artifacts=artifacts,
            recorder=recorder,
            harvester=harvester,
            limits=LIMITS,
            image_digest=SANDBOX_IMAGE,
            verifier_profile_hash=VERIFIER_PROFILE_HASH,
        )

        # What the isolated store already held. Recorded rather than deleted: a smoke run or
        # an interrupted campaign leaves real executions behind, and erasing them to make a
        # total look round is exactly the kind of tidying that turns evidence into a claim.
        report["store_before_campaign"] = {
            "coding_repair_observations": len(
                await learned.list_observations(surface=CODING_REPAIR_SURFACE, limit=500)
            ),
            "note": "prior real executions in the isolated C3 pair; not deleted, subtracted",
        }

        # ------------------------------------------------------------- S21C3-031
        completed, bundles = await _completed_runs(ledger, resume_from)
        report["resumed_from"] = {
            "file": None if resume_from is None else resume_from.as_posix(),
            "already_recorded_run_identities": len(completed),
        }
        templates = available_templates()[: task_limit or len(available_templates())]
        strategies = offline_strategies()
        executed: list[TaskRuns] = []
        # The scratch tree spans the whole pipeline, not just execution: the Corpus Factory
        # reads each task's pristine workspace off disk, so it has to still be there.
        with tempfile.TemporaryDirectory(prefix="cogos-c3-campaign-") as scratch:
            for index, template_id in enumerate(templates):
                print(f"[{index + 1}/{len(templates)}] {template_id}", file=sys.stderr)
                executed.append(
                    await runner.run_task(
                        template_id,
                        root=Path(scratch) / template_id.replace(".", "_"),
                        strategies=strategies,
                        generated_at=GENERATION_EPOCH,
                        completed=completed,
                        bundle_artifact=await _bundle_ref(artifacts, bundles.get(template_id)),
                    )
                )

            report["execution"] = _execution_report(executed)
            report["resume"] = await _resume_report(ledger, executed)

            # --------------------------------------------------------- S21C3-034
            trajectories, compiled = await _compile_trajectories(
                executed, artifacts, PostgresExperienceRepository(engine)
            )
            report["trajectories"] = trajectories

            # --------------------------------------------------------- S21C3-035
            report["corpus"] = await _route_corpus(executed, compiled, artifacts, engine)

        # ------------------------------------------------------------- S21C3-033
        report["benchmark_replay"] = await _replay_benchmarks(intake)

        # ------------------------------------------------------------- S21C3-036
        report["learned_evidence"] = await _learned_evidence(
            learned,
            learned_repository,
            artifacts,
            prior=report["store_before_campaign"]["coding_repair_observations"],  # type: ignore[index]
        )

        report["storage"] = {
            "database": database_url.rsplit("/", 1)[-1],
            "artifact_root": str(artifact_root),
            "inconsistent_development_pair_writes": 0,
        }
        report["main_worktree_mutations"] = 0 if _git_state() == tree_before else "CHANGED"
        report["started_at"] = started.isoformat()
        report["finished_at"] = utc_now().isoformat()
    finally:
        await engine.dispose()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output.as_posix())
    return 0 if report["main_worktree_mutations"] == 0 else 1


async def _bundle_ref(artifacts: ArtifactService, artifact_id: UUID | None):  # type: ignore[no-untyped-def]
    """Resolve a bundle artifact recorded by an earlier run, or `None` to write a new one."""
    return None if artifact_id is None else await artifacts.describe(artifact_id)


def _execution_report(executed: list[TaskRuns]) -> dict[str, object]:
    """Counts read from the recorded references, not from a tally kept while running."""
    runs = [item for task in executed for item in task.all_runs]
    count = count_outcomes([item.step.reference for item in runs])
    by_strategy: Counter[str] = Counter()
    visible_failures: list[str] = []
    hidden_disagreements: list[str] = []
    for item in runs:
        label = "baseline" if item.strategy is None else item.strategy.value
        by_strategy[label] += 1
        if item.visible_exit_code != 0:
            visible_failures.append(f"{item.template_id}/{label}")
        expected = item.strategy is not None and item.strategy.family.value == "correct"
        if item.hidden_passed != expected:
            hidden_disagreements.append(f"{item.template_id}/{label}")
    return {
        "tasks": len(executed),
        "runs_recorded": len(runs),
        "unique_outcomes": count.unique,
        "duplicates_excluded": count.duplicates_excluded,
        "hidden_passed": count.passed,
        "hidden_failed": count.failed,
        "by_strategy": dict(sorted(by_strategy.items())),
        "published_suite_failures": visible_failures,
        "hidden_result_disagreements": hidden_disagreements,
        "replayed_runs": sum(1 for item in runs if item.replayed),
        "task_run_ids": [str(item.step.reference.task_run_id) for item in runs],
        "bundle_artifacts": {task.template_id: str(task.bundle_artifact_id) for task in executed},
    }


async def _resume_report(
    ledger: RealityCampaignLedger, executed: list[TaskRuns]
) -> dict[str, object]:
    """Ask the Event Store whether the campaign is complete. Never ask this process."""
    planned: list[RealityRunIdentity] = [
        item.identity for task in executed for item in task.all_runs
    ]
    task_run_ids = [item.step.reference.task_run_id for task in executed for item in task.all_runs]
    manifest = RealityCampaignManifest(
        campaign_id=uuid5(CAMPAIGN_NAMESPACE, f"c3-offline:{len(planned)}"),
        campaign_version=1,
        planned_runs=tuple(planned),
        verifier_profile_hash=VERIFIER_PROFILE_HASH,
        created_at=utc_now(),
    )
    plan = await ledger.plan_resume(manifest, task_run_ids=task_run_ids)
    recorded, _ = await ledger.recorded_runs(manifest, task_run_ids=task_run_ids)
    return {
        "planned": len(planned),
        "completed": len(plan.completed),
        "remaining": len(plan.remaining),
        "is_complete": plan.is_complete,
        "unique_from_event_store": count_outcomes(recorded).unique,
    }


async def _compile_trajectories(
    executed: list[TaskRuns],
    artifacts: ArtifactService,
    repository: PostgresExperienceRepository,
) -> tuple[dict[str, object], list[object]]:
    compiled: list[object] = []
    planned = 0
    failures: list[str] = []
    tasks_represented: set[str] = set()
    strategies: Counter[str] = Counter()
    for task in executed:
        if task.baseline is None:
            continue
        plans = reality_trajectories.plan_paths(
            task_id=task.task.manifest.task_id,
            baseline=task.baseline.step,
            candidates={strategy: run.step for strategy, run in task.candidates.items()},
        )
        planned += len(plans)
        for plan in plans:
            try:
                request, sources, profiles = await reality_trajectories.build_request(
                    plan,
                    task=task.task.manifest,
                    artifacts=artifacts,
                    # W6-F1: the campaign epoch, not the clock. `ExperienceCompilerService`
                    # verifies a persisted manifest by recompiling the request and comparing
                    # for exact equality, and `created_at` is the manifest's only field that
                    # is not derived from the task and its outcomes. Reading a clock here made
                    # every trajectory unverifiable one second after it was written — the same
                    # defect as W1-F1 and W3-F2, in the third plane to inherit it.
                    created_at=GENERATION_EPOCH,
                )
                result = await ExperienceCompilerService(
                    ExperienceCompiler(sources, profiles), repository
                ).compile(request)
            except Exception as error:  # a failed compilation is evidence, not a crash
                failures.append(f"{task.template_id}/{plan.incorrect.value}: {error}")
                continue
            compiled.append((task, result))
            tasks_represented.add(task.template_id)
            strategies[plan.incorrect.value] += 1
            strategies[plan.correct.value] += 1
    return (
        {
            "planned": planned,
            "compiled": len(compiled),
            "unique_tasks_represented": len(tasks_represented),
            "strategy_families": dict(sorted(strategies.items())),
            "failed_compilations": failures,
            "distinct_compilation_ids": len(
                {str(item[1].manifest.compilation_id) for item in compiled}  # type: ignore[index]
            ),
        },
        compiled,
    )


async def _route_corpus(
    executed: list[TaskRuns],
    compiled: list[object],
    artifacts: ArtifactService,
    engine: object,
) -> dict[str, object]:
    config = CorpusConfiguration()
    factory = CorpusFactory(PostgresCorpusRepository(engine), artifacts, config)  # type: ignore[arg-type]
    splits: dict[str, set[str]] = {}
    statuses: Counter[str] = Counter()
    routed = 0
    quarantined: list[str] = []
    already_present: list[str] = []

    async def ingest(request, source, group: str) -> None:  # type: ignore[no-untyped-def]
        """Ingest, or report that this identity is already in the corpus under other bytes.

        A conflict here is a *finding*, not an error to route around: the item ID is derived,
        so a stored item that differs was written by an earlier revision of this pipeline.
        Overwriting it to make the total come out at 30 would be rewriting recorded material
        to fit a number, which is the one thing the corpus plane must never do.
        """
        nonlocal routed
        try:
            result = await factory.ingest(request, source)
        except CorpusConflictError:
            already_present.append(request.source_identity)
            return
        routed += len(result.items)
        for decision in result.route_decisions:
            statuses[decision.status.value] += 1
            if decision.status.value == "quarantined":
                quarantined.extend(decision.reason_codes)
        if result.manifest is not None:
            splits.setdefault(group, set()).update(
                entry.split.value for entry in result.manifest.items
            )

    for task in executed:
        manifest = task.task.manifest
        await ingest(
            reality_corpus_items.task_package_request(manifest, created_at=GENERATION_EPOCH),
            reality_corpus_items.task_package_source(
                manifest, workspace=task.task.workspace, config=config
            ),
            manifest.repository_group,
        )

    for task, result in compiled:  # type: ignore[misc]
        manifest = task.task.manifest  # type: ignore[attr-defined]
        for candidate in result.candidates:  # type: ignore[attr-defined]
            await ingest(
                reality_corpus_items.correction_request(
                    candidate, task=manifest, created_at=GENERATION_EPOCH
                ),
                reality_corpus_items.correction_source(candidate, config=config),
                manifest.repository_group,
            )

    crossing = sorted(group for group, values in splits.items() if len(values) > 1)
    return {
        "items_routed": routed,
        "route_status_counts": dict(sorted(statuses.items())),
        "quarantine_reasons": dict(sorted(Counter(quarantined).items())),
        "repository_groups": len(splits),
        "groups_crossing_splits": crossing,
        "split_profile": "sprint21c3-group-aware-split-v1",
        "training_actions_started": 0,
        "real_run_items_in_corpus": 0,
        "identities_already_in_corpus": sorted(already_present),
    }


async def _replay_benchmarks(intake: LearnedObservationIntake) -> dict[str, object]:
    """S21C3-033: execute existing governed cases again, and offer the results to intake.

    Executed, not relabelled. `scripts/benchmark_run.py` has replay executors that return a
    canned `PASSED` for manifests whose subsystem cannot run offline; none of them is used
    here. Every manifest below is driven by the adapter that actually runs the subsystem, so
    a regression in that subsystem shows up as a failed case rather than as a copied label.
    """
    run_ids: list[str] = []
    by_domain: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    references = []
    for path, executor in _BENCHMARK_EXECUTORS.items():
        manifest = load_manifest(Path(path))
        run = await BenchmarkRunner(executor, git_commit="c3-campaign").run_manifest(
            manifest, random_seed=21
        )
        run_ids.append(str(run.run_id))
        cases = {case.case_id: case for case in manifest.cases}
        for result in run.case_results:
            case = cases[result.case_id]
            by_domain[case.domain.value] += 1
            by_status[result.status.value] += 1
            references.append(_benchmark_reference(manifest, run.run_id, case, result))

    observations = await intake.offer_all(tuple(references), correlation_id=uuid4())
    return {
        "manifests": sorted(_BENCHMARK_EXECUTORS),
        "runs": run_ids,
        "cases_executed": len(references),
        "by_domain": dict(sorted(by_domain.items())),
        "by_status": dict(sorted(by_status.items())),
        "observations_recorded": len(observations),
        "accepted": sum(1 for item in observations if item.status is ObservationStatus.ACCEPTED),
        "training_eligible": sum(1 for item in observations if item.training_eligible),
    }


def _benchmark_reference(manifest, run_id, case, result):  # type: ignore[no-untyped-def]
    """One executed case as a governed outcome reference.

    `governed_benchmark_case` is a real-governed-run source kind, so provenance is
    `REAL_GOVERNED_RUN` and the observation is evaluation-only — a replayed benchmark case
    is evidence about this system, and evidence about this system is not training material.

    The evidence is the executed-against-declared comparison. These adapters carry no
    `VerificationBundle`; what independently decides the case is that the *frozen manifest*
    states the expected outcome and the adapter's `expected_outcome_matched` metric reports
    whether the execution produced it. The adapter cannot choose what was expected, so the
    hash below binds all four things that make the claim checkable: the manifest revision,
    the case, what it declared, and what the run measured. A result missing that metric
    measured nothing, and is offered as `UNKNOWN` so intake quarantines it.
    """
    identity = f"{manifest.benchmark_id}:{manifest.version}:{case.case_id}"
    decided = "expected_outcome_matched" in result.metrics
    verifier_hash = (
        sha256(
            json.dumps(
                {
                    "manifest_hash": manifest.manifest_hash,
                    "case_id": case.case_id,
                    "expected_outputs": case.expected_outputs,
                    "metrics": result.metrics,
                    "status": result.status.value,
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        if decided
        else None
    )
    return GovernedOutcomeReference(
        surface=f"benchmark.{case.domain.value}",
        source_kind="governed_benchmark_case",
        source_run_id=uuid5(CAMPAIGN_NAMESPACE, f"{run_id}:{case.case_id}"),
        source_task_id=uuid5(CAMPAIGN_NAMESPACE, identity),
        source_payload_hash=sha256(result.model_dump_json().encode()).hexdigest(),
        provenance_class=ProvenanceClass.REAL_GOVERNED_RUN,
        attribution=(
            ObservationAttribution.DIRECT
            if verifier_hash is not None
            else ObservationAttribution.UNKNOWN
        ),
        usage_rights_verified=True,
        sensitivity="public",
        verifier_status=result.status.value,
        verifier_evidence_hash=verifier_hash,
        occurred_at=result.finished_at,
    )


async def _learned_evidence(
    learned: LearnedEvidenceService,
    repository: PostgresLearnedEvidenceRepository,
    artifacts: ArtifactService,
    prior: int,
) -> dict[str, object]:
    """Observation counts and one evaluation snapshot; a training snapshot must be refused."""
    observations = await learned.list_observations(surface=CODING_REPAIR_SURFACE, limit=500)
    statuses: Counter[str] = Counter(item.status.value for item in observations)
    reasons: Counter[str] = Counter(
        item.decision_reason.split(":", 1)[0]
        for item in observations
        if item.status is not ObservationStatus.ACCEPTED
    )
    builder = LearnedDatasetBuilder(repository, LearnedArtifactStore(artifacts))
    evaluation = await builder.build(
        surface=CODING_REPAIR_SURFACE,
        corpus_role=CorpusRole.EVALUATION,
        feature_schema_hash=FEATURE_SCHEMA_HASH,
        sensitivity="public",
    )
    training_refused = False
    try:
        await builder.build(
            surface=CODING_REPAIR_SURFACE,
            corpus_role=CorpusRole.TRAINING,
            feature_schema_hash=FEATURE_SCHEMA_HASH,
            sensitivity="public",
        )
    except LearnedRepositoryError:
        training_refused = True
    return {
        "observations": len(observations),
        "observations_from_this_campaign": len(observations) - prior,
        "status_counts": dict(sorted(statuses.items())),
        "non_accepted_reasons": dict(sorted(reasons.items())),
        "evaluation_dataset_id": str(evaluation.dataset_id),
        "evaluation_observation_count": evaluation.observation_count,
        "evaluation_provenance_counts": evaluation.provenance_counts,
        "training_snapshot_containing_a_real_run_refused": training_refused,
        "real_runs_in_training": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tasks", type=int, default=None, help="run only the first N tasks")
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="a previous evidence file; its recorded runs are skipped instead of re-executed",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args.output, args.tasks, args.resume_from))


if __name__ == "__main__":
    raise SystemExit(main())
