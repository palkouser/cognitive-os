"""§6.1 steps 8 and 9, against a real sandbox: does a C3 outcome reach the downstream planes?

W1 proved steps 1 to 7 and 10 — generation, hidden verification, outcome artifacts, the
event, learned intake, replay. It did not prove that anything *downstream* accepts the
result, and a learning input nothing can consume is not a learning input. This is the
smallest thing that answers both remaining questions, and it answers them the only way they
can be answered: by running three real containers and feeding what comes out into the real
Experience Compiler and the real Corpus Factory.

One test, because the two steps are one claim: the compiler reconstructs the failure, the
correction and the recovery from the recorded runs, and the Corpus Factory then routes the
task package and that compiled correction into the *same* group-aware split with no control
material attached. The refusal cases need no container and live in
`tests/cognitive_os/coding/test_reality_downstream.py`.

Enable with `COGOS_RUN_SANDBOX_INTEGRATION=1` after `scripts/sandbox_build.sh`.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.application.services.experience_compiler import ExperienceCompilerService
from cognitive_os.coding import reality_candidates, reality_corpus_items, reality_trajectories
from cognitive_os.coding.hidden_verification import HiddenVerificationRunner, load_bundle
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import apply_candidate, write_task
from cognitive_os.coding.reality_trajectories import CorrectionStep
from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.repository import InMemoryCorpusRepository
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.corpus import CorpusRouteStatus
from cognitive_os.domain.experience import CompilationDecisionType
from cognitive_os.domain.reality import (
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.domain.sandbox import SandboxLimits
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.repository import InMemoryExperienceRepository
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox
from tests.cognitive_os.coding.reality_fixtures import (
    InMemoryArtifactStore,
    coding_outcome,
    digest,
)

SANDBOX_IMAGE = os.environ.get("COGOS_SANDBOX_IMAGE", "cognitive-os-sandbox:sprint-5")

LIMITS = SandboxLimits(
    timeout_seconds=120,
    memory_bytes=536_870_912,
    cpu_count=1,
    pid_limit=128,
    maximum_stdout_bytes=200_000,
    maximum_stderr_bytes=200_000,
    maximum_artifact_bytes=200_000,
)

TEMPLATE_ID = "numeric_logic.mean"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("COGOS_RUN_SANDBOX_INTEGRATION") != "1",
        reason="opt-in rootless Docker test",
    ),
]


class _Slice:
    """One task executed three times, with everything the downstream planes will ask for."""

    def __init__(self, root: Path) -> None:
        self.artifacts = InMemoryArtifactStore()
        self.events = MemoryEventStore()
        self.recorder = CodingOutcomeRecorder(
            self.artifacts, CodingEventService(self.events), self.events
        )
        self.sandbox = DockerSandbox(SANDBOX_IMAGE)
        self.runner = HiddenVerificationRunner(
            sandbox=self.sandbox, limits=LIMITS, image_digest=SANDBOX_IMAGE
        )
        self.root = root
        self.task = write_task(
            TEMPLATE_ID,
            root=root / "task",
            seed=1,
            hidden_bundle_artifact_id=uuid4(),
            hidden_bundle_hash=digest("placeholder"),
            created_at=utc_now(),
        )
        self.manifest = self.task.manifest
        self.bundle = load_bundle(
            task_id=self.manifest.task_id,
            host_path=self.task.control,
            artifact_id=uuid4(),
            artifact_hash=digest("control archive"),
        )

    async def run(self, strategy: RealityCandidateStrategy | None) -> CorrectionStep:
        label = "baseline" if strategy is None else strategy.value
        workspace = self.root / f"run-{label}"
        shutil.copytree(self.task.workspace, workspace)
        candidate = None
        if strategy is not None:
            apply_candidate(self.task, strategy, workspace=workspace)
            generated = reality_candidates.build_candidate(self.manifest, strategy)
            patch = await self.artifacts.put_bytes(
                generated.unified_diff.encode(), media_type="text/x-diff"
            )
            candidate = reality_candidates.build_manifest(
                self.manifest,
                generated,
                patch_artifact_id=patch.artifact_id,
                created_at=utc_now(),
            )
        task_run_id = uuid4()
        evidence = await self.runner.run(
            task_id=self.manifest.task_id,
            task_run_id=task_run_id,
            workspace=workspace,
            bundle=self.bundle,
        )
        recorded = await self.recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=(
                    CodingOutcomeStatus.ACCEPTED if evidence.passed else CodingOutcomeStatus.FAILED
                ),
                marker=label,
            ),
            task=self.manifest,
            evidence=evidence,
            candidate=candidate,
            correlation_id=task_run_id,
            run_identity=RealityRunIdentity(
                task_id=self.manifest.task_id,
                task_manifest_hash=self.manifest.content_hash,
                run_kind=(
                    RealityRunKind.BASELINE if strategy is None else RealityRunKind.CANDIDATE
                ),
                candidate_id=None if candidate is None else candidate.candidate_id,
                strategy=strategy,
                source=(
                    RealityCandidateSource.BASELINE
                    if strategy is None
                    else RealityCandidateSource.CURATED
                ),
                generator_profile_id="reality.tasks",
                verifier_profile_hash=digest("c3 verifier profile"),
                campaign_version=1,
            ),
        )
        return CorrectionStep(reference=recorded.reference, candidate=candidate)


@pytest.mark.asyncio
async def test_a_recorded_run_reaches_the_compiler_and_the_corpus(tmp_path: Path) -> None:
    item = _Slice(tmp_path)
    baseline = await item.run(None)
    incomplete = await item.run(RealityCandidateStrategy.INCOMPLETE_A)
    correct = await item.run(RealityCandidateStrategy.CORRECT_NARROW)

    assert not baseline.reference.hidden_verification_passed
    assert not incomplete.reference.hidden_verification_passed
    assert correct.reference.hidden_verification_passed

    # ---------------------------------------------------------------- §6.1 step 8
    plans = reality_trajectories.plan_paths(
        task_id=item.manifest.task_id,
        baseline=baseline,
        candidates={
            RealityCandidateStrategy.INCOMPLETE_A: incomplete,
            RealityCandidateStrategy.CORRECT_NARROW: correct,
        },
    )
    assert len(plans) == 1, "only path A has both of its candidate runs"

    request, sources, profiles = await reality_trajectories.build_request(
        plans[0], task=item.manifest, artifacts=item.artifacts, created_at=utc_now()
    )
    service = ExperienceCompilerService(
        ExperienceCompiler(sources, profiles), InMemoryExperienceRepository()
    )
    compiled = await service.compile(request)

    assert compiled.decision.decision in {
        CompilationDecisionType.COMPLETED,
        CompilationDecisionType.COMPLETED_WITH_WARNINGS,
    }, compiled.decision
    # The failure, the fix, and the link between them: a trajectory without all three is a
    # log, not a correction.
    assert compiled.analysis.failed_branches, "the baseline and incomplete runs failed"
    assert compiled.analysis.corrections, "two candidate patches were applied"
    assert any(path.resolved for path in compiled.analysis.recovery_paths)
    assert compiled.analysis.successful_path is not None
    assert compiled.candidates, "a compiled trajectory yields at least one experience candidate"

    # Recompiling the same path is the same compilation, not a second one.
    again, _, _ = await reality_trajectories.build_request(
        plans[0], task=item.manifest, artifacts=item.artifacts, created_at=utc_now()
    )
    assert again.compilation_id == request.compilation_id
    assert again.idempotency_key == request.idempotency_key

    # ---------------------------------------------------------------- §6.1 step 9
    config = CorpusConfiguration()
    factory = CorpusFactory(InMemoryCorpusRepository(), item.artifacts, config)
    now = utc_now()

    task_result = await factory.ingest(
        reality_corpus_items.task_package_request(item.manifest, created_at=now),
        reality_corpus_items.task_package_source(
            item.manifest, workspace=item.task.workspace, config=config
        ),
    )
    correction_result = await factory.ingest(
        reality_corpus_items.correction_request(
            compiled.candidates[0], task=item.manifest, created_at=now
        ),
        reality_corpus_items.correction_source(compiled.candidates[0], config=config),
    )

    assert task_result.items and correction_result.items
    assert task_result.manifest is not None
    assert correction_result.manifest is not None

    # Same repository group, so the same split. Two variants of one task on opposite sides
    # of an evaluation boundary is the leak a group-aware split exists to prevent.
    task_splits = {entry.split for entry in task_result.manifest.items}
    correction_splits = {entry.split for entry in correction_result.manifest.items}
    assert len(task_splits) == 1
    assert task_splits == correction_splits
    assert task_result.manifest.split_manifest.profile_id == "sprint21c3-group-aware-split-v1"

    # Nothing was denied for want of rights, and no hidden test travelled with the package.
    assert all(
        decision.status is not CorpusRouteStatus.DENIED
        for decision in (*task_result.route_decisions, *correction_result.route_decisions)
    )
    packaged = task_result.source_manifest.model_dump_json()
    assert "test_hidden_" not in packaged
    assert item.bundle.bundle_content_hash not in packaged
