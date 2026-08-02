"""Execute the offline coding campaign, §S21C3-031.

The loop is small on purpose. Everything it needs already exists — the task generator writes
a workspace and a control bundle, `HiddenVerificationRunner` mounts the bundle read-only and
runs the hidden suite, `CodingOutcomeRecorder` writes the outcome bytes and appends the event,
`RealityCampaignLedger` says what still has to run. What this adds is the ordering, and three
invariants that only a runner can hold:

*Nothing outside the run's own copy is written.* Each run gets a fresh copy of the pristine
workspace. After every run the pristine tree and the control bundle are re-hashed; a campaign
that mutated its own source would produce a corpus in which later tasks were repaired by
earlier ones, and the mutation would be invisible in the outcomes.

*A restart does not re-run finished work.* Which runs are still outstanding is decided by
`RealityCampaignLedger` from the Event Store, not by this runner and not from any process's
memory, because the process is what a crash destroys. The runner executes what it is given.

*A run that could not be measured is recorded, not dropped.* An unverifiable hidden result is
an outcome with `UNKNOWN` attribution, which intake quarantines. Silently skipping it would
make the denominator smaller and the success rate better.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.sandbox import SandboxPort
from cognitive_os.application.services.reality_outcome_harvester import RealityOutcomeHarvester
from cognitive_os.coding import reality_candidates
from cognitive_os.coding.hidden_verification import (
    HiddenVerificationBundle,
    HiddenVerificationRunner,
    load_bundle,
)
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import GeneratedTask, apply_candidate, write_task
from cognitive_os.coding.reality_trajectories import CorrectionStep
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType
from cognitive_os.domain.coding import (
    CodingOutcome,
    CodingOutcomeStatus,
    RepositoryProfile,
    RepositoryProfileStatus,
    WorkspaceDisposition,
)
from cognitive_os.domain.common import ArtifactRef, utc_now
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityOutcomeReference,
    RealityRunIdentity,
    RealityRunKind,
    RealityTaskManifest,
)
from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest
from cognitive_os.providers.workspace_snapshot import snapshot_workspace

#: The published test command every generated task carries. Running it is what proves the
#: campaign is measuring a hidden defect rather than a broken workspace.
VISIBLE_PYTEST_ARGUMENTS = ("-q", "-p", "no:cacheprovider", "tests")

ACCEPTANCE_POLICY_ID = "cognitive-os:sprint21c3:python-coding-hidden-acceptance"


class CampaignRunError(RuntimeError):
    """A run could not be executed or recorded in a state worth keeping."""


class WorkspaceIntegrityError(CampaignRunError):
    """A run changed something outside its own copy."""


@dataclass(frozen=True, slots=True)
class ExecutedRun:
    """One recorded execution, plus what the campaign needs to reason about it."""

    template_id: str
    identity: RealityRunIdentity
    step: CorrectionStep
    visible_exit_code: int
    replayed: bool

    @property
    def strategy(self) -> RealityCandidateStrategy | None:
        return self.identity.strategy

    @property
    def hidden_passed(self) -> bool:
        return self.step.reference.hidden_verification_passed


@dataclass(frozen=True, slots=True)
class PreparedTask:
    """A task package on disk, plus the two digests that say it was not disturbed.

    Held as a value rather than as loop variables inside `run_task` because a caller that
    executes candidates one at a time still has to re-check the same two things after each of
    them: a campaign that repaired its own source would produce a corpus where later tasks were
    fixed by earlier ones, and nothing in the outcomes would show it.
    """

    template_id: str
    root: Path
    generated: GeneratedTask
    bundle: HiddenVerificationBundle
    bundle_artifact: ArtifactRef
    generated_at: datetime
    pristine_digest: str
    control_digest: str


@dataclass
class TaskRuns:
    """Every run recorded for one task, in the order the manifest asked for them.

    S21D2-021. `candidates` used to be keyed by `RealityCandidateStrategy` and `all_runs`
    sorted those keys alphabetically, which quietly discarded the manifest's ordering: a
    campaign that asked for a deterministically shuffled candidate order got the same
    alphabetical order for every task. That is harmless while nothing reads the order, and it
    is the whole experiment once a ranker permutes it — so the key is now the opaque candidate
    ID and the order is insertion order, which is execution order, which is manifest order.
    """

    template_id: str
    task: GeneratedTask
    bundle_artifact_id: UUID | None = None
    baseline: ExecutedRun | None = None
    candidates: dict[UUID, ExecutedRun] = field(default_factory=dict)

    @property
    def all_runs(self) -> tuple[ExecutedRun, ...]:
        ordered = [] if self.baseline is None else [self.baseline]
        ordered.extend(self.candidates.values())
        return tuple(ordered)

    def by_strategy(self, strategy: RealityCandidateStrategy) -> ExecutedRun | None:
        """For C3 callers that named a recipe. D2 code addresses candidates by ID."""
        return next(
            (run for run in self.candidates.values() if run.identity.strategy is strategy), None
        )


class RealityCampaignRunner:
    """Runs baselines and candidates, records what happened, and touches nothing else."""

    def __init__(
        self,
        *,
        sandbox: SandboxPort,
        artifacts: ArtifactStorePort,
        recorder: CodingOutcomeRecorder,
        harvester: RealityOutcomeHarvester | None,
        limits: SandboxLimits,
        image_digest: str,
        campaign_version: int = 1,
        verifier_profile_hash: str,
    ) -> None:
        self._sandbox = sandbox
        self._artifacts = artifacts
        self._recorder = recorder
        self._harvester = harvester
        self._limits = limits
        self._image = image_digest
        self._campaign_version = campaign_version
        self._verifier_profile_hash = verifier_profile_hash
        self._hidden = HiddenVerificationRunner(
            sandbox=sandbox, limits=limits, image_digest=image_digest
        )

    async def run_task(
        self,
        template_id: str,
        *,
        root: Path,
        seed: int = 1,
        strategies: Sequence[RealityCandidateStrategy],
        generated_at: datetime,
        completed: Mapping[str, RealityOutcomeReference] = MappingProxyType({}),
        bundle_artifact: ArtifactRef | None = None,
        candidate_ids: Mapping[RealityCandidateStrategy, UUID] | None = None,
    ) -> TaskRuns:
        """Execute the baseline and every requested candidate for one task.

        `generated_at` is a campaign constant, not a clock read. `RealityTaskManifest`
        hashes its own `created_at`, so a wall-clock value would give the same task a
        different manifest revision on every run — and the manifest hash is what binds an
        outcome to its task, what a resumed campaign matches against, and what the corpus
        plane deduplicates on. A task generated twice has to be the same task.

        `completed` maps run-identity keys to the outcomes the Event Store already holds for
        them. Those runs are skipped rather than re-executed: 150 containers is the cost of a
        crash, and a resume that re-ran them would pay it twice for nothing. The stored
        reference is reused as-is, so a resumed campaign reports the original execution rather
        than a fresh one that happens to agree.

        `bundle_artifact` is the other half of that. The Artifact Store mints a fresh metadata
        row for every write, even of identical bytes, and the manifest names its bundle by
        artifact ID — so writing the bundle again would give the same task a new manifest hash
        and a new run identity, and resume would match nothing. A resumed campaign passes back
        the artifact its first run recorded.

        `candidate_ids` is how a D2 campaign runs a *sealed* task: the catalogue named every
        candidate by position before anything was executed, so re-deriving an identity from the
        recipe here would record a run under a name the seal never committed to. Absent, the C3
        derivation is unchanged.
        """
        prepared = await self.prepare_task(
            template_id,
            root=root,
            seed=seed,
            generated_at=generated_at,
            bundle_artifact=bundle_artifact,
        )
        generated = prepared.generated

        runs = TaskRuns(
            template_id=template_id,
            task=generated,
            bundle_artifact_id=prepared.bundle_artifact.artifact_id,
        )
        runs.baseline = await self.run_baseline(prepared, completed=completed)
        for strategy in strategies:
            executed = await self.run_candidate(
                prepared,
                strategy,
                completed=completed,
                candidate_id=None if candidate_ids is None else candidate_ids[strategy],
            )
            # Keyed by the candidate the run actually executed, so nothing downstream has to
            # know the recipe to address it, and two recipes cannot collide onto one slot.
            candidate_id = executed.identity.candidate_id
            if candidate_id is None:  # pragma: no cover - a candidate run always names one
                raise CampaignRunError("a candidate run recorded no candidate identity")
            runs.candidates[candidate_id] = executed
        return runs

    async def prepare_task(
        self,
        template_id: str,
        *,
        root: Path,
        seed: int = 1,
        generated_at: datetime,
        bundle_artifact: ArtifactRef | None = None,
    ) -> PreparedTask:
        """Materialise one task package and record what must not change while it runs.

        Split out of `run_task` so a caller that decides *which* candidate runs next — the D2
        sequencer, whose whole job is that decision — can drive the runs one at a time without
        re-writing the package between them. `run_task` is this plus a fixed order.
        """
        if bundle_artifact is None:
            bundle_artifact = await self._artifacts.put_bytes(
                f"reality-control:{template_id}:{seed}".encode(),
                media_type="application/json",
            )
        generated = write_task(
            template_id,
            root=root,
            seed=seed,
            hidden_bundle_artifact_id=bundle_artifact.artifact_id,
            hidden_bundle_hash=bundle_artifact.content_hash,
            created_at=generated_at,
        )
        bundle = load_bundle(
            task_id=generated.manifest.task_id,
            host_path=generated.control,
            artifact_id=bundle_artifact.artifact_id,
            artifact_hash=bundle_artifact.content_hash,
        )
        return PreparedTask(
            template_id=template_id,
            root=root,
            generated=generated,
            bundle=bundle,
            bundle_artifact=bundle_artifact,
            generated_at=generated_at,
            pristine_digest=snapshot_workspace(generated.workspace).digest,
            control_digest=bundle.bundle_content_hash,
        )

    async def run_baseline(
        self,
        prepared: PreparedTask,
        *,
        completed: Mapping[str, RealityOutcomeReference] = MappingProxyType({}),
    ) -> ExecutedRun:
        """The unrepaired package, which must fail its hidden suite for the task to be one."""
        executed = await self._execute(
            prepared.generated,
            prepared.bundle,
            None,
            root=prepared.root,
            generated_at=prepared.generated_at,
            completed=completed,
        )
        self._require_untouched(prepared, label="baseline")
        return executed

    async def run_candidate(
        self,
        prepared: PreparedTask,
        strategy: RealityCandidateStrategy,
        *,
        completed: Mapping[str, RealityOutcomeReference] = MappingProxyType({}),
        candidate_id: UUID | None = None,
    ) -> ExecutedRun:
        """One candidate, executed and recorded, with the package re-checked afterwards."""
        executed = await self._execute(
            prepared.generated,
            prepared.bundle,
            strategy,
            root=prepared.root,
            generated_at=prepared.generated_at,
            completed=completed,
            candidate_id=candidate_id,
        )
        if executed.identity.candidate_id is None:  # pragma: no cover - always names one
            raise CampaignRunError("a candidate run recorded no candidate identity")
        self._require_untouched(prepared, label=strategy.value)
        return executed

    async def _execute(
        self,
        generated: GeneratedTask,
        bundle: HiddenVerificationBundle,
        strategy: RealityCandidateStrategy | None,
        *,
        root: Path,
        generated_at: datetime,
        completed: Mapping[str, RealityOutcomeReference],
        candidate_id: UUID | None = None,
    ) -> ExecutedRun:
        manifest = generated.manifest
        label = "baseline" if strategy is None else strategy.value
        candidate = None
        if strategy is not None:
            candidate = await self._candidate_manifest(
                manifest, strategy, generated_at, candidate_id=candidate_id
            )
        identity = RealityRunIdentity(
            task_id=manifest.task_id,
            task_manifest_hash=manifest.content_hash,
            run_kind=RealityRunKind.BASELINE if strategy is None else RealityRunKind.CANDIDATE,
            candidate_id=None if candidate is None else candidate.candidate_id,
            strategy=strategy,
            source=(
                RealityCandidateSource.BASELINE
                if strategy is None
                else RealityCandidateSource.CURATED
            ),
            generator_profile_id=manifest.generator_profile_id,
            verifier_profile_hash=self._verifier_profile_hash,
            campaign_version=self._campaign_version,
        )

        done = completed.get(identity.key)
        if done is not None:
            return ExecutedRun(
                template_id=generated.template.template_id,
                identity=identity,
                step=CorrectionStep(reference=done, candidate=candidate),
                visible_exit_code=0,
                replayed=True,
            )

        workspace = root / f"run-{label}"
        if workspace.exists():
            shutil.rmtree(workspace)
        shutil.copytree(generated.workspace, workspace)
        try:
            if strategy is not None:
                apply_candidate(generated, strategy, workspace=workspace)
            visible = await self._visible_exit_code(workspace)
            evidence = await self._hidden.run(
                task_id=manifest.task_id,
                task_run_id=(task_run_id := uuid4()),
                workspace=workspace,
                bundle=bundle,
            )
            recorded = await self._recorder.record(
                outcome=self._outcome(task_run_id, evidence.passed, label),
                task=manifest,
                evidence=evidence,
                candidate=candidate,
                correlation_id=task_run_id,
                run_identity=identity,
            )
        finally:
            # The workspace is a copy and nothing reads it after the run. Leaving 150 of them
            # behind is how a campaign fills a disk halfway through.
            shutil.rmtree(workspace, ignore_errors=True)

        if self._harvester is not None:
            await self._harvester.harvest(
                event_id=recorded.reference.source_event_id,
                task=manifest,
                correlation_id=task_run_id,
            )
        return ExecutedRun(
            template_id=generated.template.template_id,
            identity=identity,
            step=CorrectionStep(reference=recorded.reference, candidate=candidate),
            visible_exit_code=visible,
            replayed=recorded.replayed,
        )

    async def _candidate_manifest(
        self,
        manifest: RealityTaskManifest,
        strategy: RealityCandidateStrategy,
        generated_at: datetime,
        *,
        candidate_id: UUID | None = None,
    ) -> RealityCandidateManifest:
        """Store the patch bytes, then name them. The trajectory plane reads them back."""
        generated = reality_candidates.build_candidate(
            manifest, strategy, candidate_id=candidate_id
        )
        patch = await self._artifacts.put_bytes(
            generated.unified_diff.encode(),
            media_type=reality_candidates.CANDIDATE_PATCH_MEDIA_TYPE,
        )
        if patch.content_hash != generated.patch_hash:  # pragma: no cover - defensive
            raise CampaignRunError("stored patch bytes do not match the generated candidate")
        return reality_candidates.build_manifest(
            manifest,
            generated,
            patch_artifact_id=patch.artifact_id,
            created_at=generated_at,
        )

    async def _visible_exit_code(self, workspace: Path) -> int:
        """Run the published suite. No control bundle is mounted, by construction."""
        sandbox_id = f"cogos-campaign-v-{uuid4().hex[:12]}"
        try:
            result = await self._sandbox.run(
                SandboxRequest(
                    sandbox_id=sandbox_id,
                    tool_call_id=str(uuid4()),
                    task_run_id=str(uuid4()),
                    workspace=str(workspace),
                    executable="pytest",
                    arguments=VISIBLE_PYTEST_ARGUMENTS,
                    limits=self._limits,
                )
            )
            return int(result.exit_code)
        finally:
            await self._sandbox.cleanup(sandbox_id)

    @staticmethod
    def _require_untouched(prepared: PreparedTask, *, label: str) -> None:
        generated = prepared.generated
        where = f"{generated.template.template_id}/{label}"
        if snapshot_workspace(generated.workspace).digest != prepared.pristine_digest:
            raise WorkspaceIntegrityError(f"{where}: the pristine workspace changed during a run")
        if snapshot_workspace(generated.control).digest != prepared.control_digest:
            raise WorkspaceIntegrityError(f"{where}: the control bundle changed during a run")

    @staticmethod
    def _outcome(task_run_id: UUID, passed: bool, label: str) -> CodingOutcome:
        status = CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED
        return CodingOutcome(
            task_run_id=task_run_id,
            status=status,
            repository_profile=RepositoryProfile(
                status=RepositoryProfileStatus.SUPPORTED,
                git_repository=False,
                has_pyproject=True,
                has_pytest=True,
            ),
            base_commit="0" * 40,
            acceptance_decision=(
                _acceptance(task_run_id) if status is CodingOutcomeStatus.ACCEPTED else None
            ),
            workspace_disposition=WorkspaceDisposition.REMOVE,
            policy_denials=(label,),
            completed_at=utc_now(),
        )


def _acceptance(task_run_id: UUID) -> AcceptanceDecision:
    return AcceptanceDecision(
        decision_id=uuid5(NAMESPACE_URL, f"cognitive-os:c3:acceptance:{task_run_id}"),
        task_run_id=task_run_id,
        policy_id=uuid5(NAMESPACE_URL, ACCEPTANCE_POLICY_ID),
        policy_version="1",
        decision=AcceptanceDecisionType.ACCEPTED,
        criterion_evaluations=(),
        required_passed=True,
        optional_score=1.0,
        reason="every required criterion passed, including hidden verification",
        created_at=utc_now(),
    )
