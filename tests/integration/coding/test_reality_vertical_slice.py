"""The Sprint 21C3 §6.1 first vertical slice, against a real rootless Docker sandbox.

Opt-in, like every other sandbox test in this directory: normal CI has no Docker daemon and
no sandbox image, and a slice that silently skipped would be a green tick for work nobody
ran. Enable with `COGOS_RUN_SANDBOX_INTEGRATION=1` after `scripts/sandbox_build.sh`.

What this proves that no unit test can: the control bundle really is mounted read-only at
`/verification`, the workspace really is the only writable mount, and a patch that satisfies
every published test really does fail the hidden suite.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.application.services.reality_campaign import (
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_outcome_harvester import (
    RealityOutcomeHarvester,
)
from cognitive_os.coding.hidden_verification import (
    HiddenVerificationRunner,
    HiddenVerificationStatus,
    load_bundle,
)
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import apply_candidate, write_task
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import ObservationStatus
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityRunIdentity,
    RealityRunKind,
)
from cognitive_os.domain.sandbox import (
    SandboxLimits,
    SandboxRequest,
    SandboxVerificationInput,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox
from tests.cognitive_os.coding.reality_fixtures import (
    InMemoryArtifactStore,
    candidate_manifest,
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

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("COGOS_RUN_SANDBOX_INTEGRATION") != "1",
        reason="opt-in rootless Docker test",
    ),
]

VISIBLE_CONFTEST = (
    "import pathlib\nimport sys\n\nsys.path.insert(0, str(pathlib.Path(__file__).parent / 'src'))\n"
)


async def _visible_pytest(sandbox: DockerSandbox, workspace: Path) -> int:
    sandbox_id = f"cogos-visible-{uuid4().hex[:12]}"
    try:
        result = await sandbox.run(
            SandboxRequest(
                sandbox_id=sandbox_id,
                tool_call_id=str(uuid4()),
                task_run_id=str(uuid4()),
                workspace=str(workspace),
                executable="pytest",
                arguments=("-q", "-p", "no:cacheprovider", "tests"),
                limits=LIMITS,
            )
        )
        return result.exit_code
    finally:
        await sandbox.cleanup(sandbox_id)


@pytest.mark.asyncio
async def test_first_vertical_slice_end_to_end(tmp_path: Path) -> None:
    sandbox = DockerSandbox(SANDBOX_IMAGE)
    artifacts = InMemoryArtifactStore()
    events = MemoryEventStore()
    recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)
    intake = LearnedObservationIntake(
        LearnedEvidenceService(
            InMemoryLearnedEvidenceRepository(), events=LearnedEventService(events)
        )
    )
    harvester = RealityOutcomeHarvester(artifacts, events, intake)
    ledger = RealityCampaignLedger(events)

    # 1. deterministic task generation
    bundle_artifact_id = uuid4()
    task = write_task(
        "numeric_logic.empty_mean",
        root=tmp_path / "task",
        seed=1,
        hidden_bundle_artifact_id=bundle_artifact_id,
        hidden_bundle_hash=digest("placeholder"),
        created_at=utc_now(),
    )
    bundle = load_bundle(
        task_id=task.manifest.task_id,
        host_path=task.control,
        artifact_id=bundle_artifact_id,
        artifact_hash=digest("control archive"),
    )
    manifest = task.manifest
    runner = HiddenVerificationRunner(sandbox=sandbox, limits=LIMITS, image_digest=SANDBOX_IMAGE)

    async def run_one(label: str, strategy: RealityCandidateStrategy | None) -> tuple[object, int]:
        workspace = tmp_path / f"run-{label}"
        shutil.copytree(task.workspace, workspace)
        (workspace / "conftest.py").write_text(VISIBLE_CONFTEST)
        if strategy is not None:
            apply_candidate(task, strategy, workspace=workspace)
        visible_exit = await _visible_pytest(sandbox, workspace)
        task_run_id = uuid4()
        evidence = await runner.run(
            task_id=manifest.task_id,
            task_run_id=task_run_id,
            workspace=workspace,
            bundle=bundle,
        )
        candidate = None if strategy is None else candidate_manifest(manifest, strategy)
        identity = RealityRunIdentity(
            task_id=manifest.task_id,
            task_manifest_hash=manifest.content_hash,
            run_kind=RealityRunKind.BASELINE if strategy is None else RealityRunKind.CANDIDATE,
            candidate_id=None if candidate is None else candidate.candidate_id,
            strategy=strategy,
            source=RealityCandidateSource.BASELINE
            if strategy is None
            else RealityCandidateSource.CURATED,
            generator_profile_id="reality.tasks",
            verifier_profile_hash=digest("c3 verifier profile"),
            campaign_version=1,
        )
        recorded = await recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=CodingOutcomeStatus.ACCEPTED
                if evidence.passed
                else CodingOutcomeStatus.FAILED,
                marker=label,
            ),
            task=manifest,
            evidence=evidence,
            candidate=candidate,
            correlation_id=task_run_id,
            run_identity=identity,
        )
        assert evidence.status in {
            HiddenVerificationStatus.PASSED,
            HiddenVerificationStatus.FAILED,
        }, evidence.reason
        return (recorded, evidence, identity, task_run_id, candidate), visible_exit

    # 2. the baseline fails the hidden suite while passing every published test
    (
        (baseline, baseline_evidence, baseline_identity, baseline_run, _baseline_candidate),
        baseline_visible,
    ) = await run_one("baseline", None)
    assert baseline_visible == 0, "the published contract must not reveal the defect"
    assert baseline_evidence.status is HiddenVerificationStatus.FAILED

    # 3. an incomplete candidate also satisfies the published contract and still fails
    (
        (
            incomplete,
            incomplete_evidence,
            incomplete_identity,
            incomplete_run,
            _incomplete_candidate,
        ),
        incomplete_visible,
    ) = await run_one("incomplete_a", RealityCandidateStrategy.INCOMPLETE_A)
    assert incomplete_visible == 0, "a visible-test-only patch must look correct"
    assert incomplete_evidence.status is HiddenVerificationStatus.FAILED

    # 4. the correct candidate passes both
    (
        (correct, correct_evidence, correct_identity, correct_run, correct_candidate),
        correct_visible,
    ) = await run_one("correct_narrow", RealityCandidateStrategy.CORRECT_NARROW)
    assert correct_visible == 0
    assert correct_evidence.status is HiddenVerificationStatus.PASSED

    # 5 and 6. every outcome resolves to bytes and to an event
    for recorded in (baseline, incomplete, correct):
        reference = recorded.reference
        assert await artifacts.verify(reference.outcome_artifact_id)
        assert await artifacts.verify(reference.hidden_evidence_artifact_id)
        stored = await events.get_event(reference.source_event_id)
        assert stored is not None
        assert stored.envelope.event_type == "coding.outcome_recorded"

    # 7. learned intake accepts them as evaluation-only evidence
    harvested = await harvester.harvest(
        event_id=correct.reference.source_event_id, task=manifest, correlation_id=uuid4()
    )
    assert harvested.governed.provenance_class is ProvenanceClass.REAL_GOVERNED_RUN
    assert harvested.observation.status is ObservationStatus.ACCEPTED
    assert harvested.evaluation_eligible is True

    # 8. the denominator is three, and nothing is counted twice
    references = [item.reference for item in (baseline, incomplete, correct)]
    count = count_outcomes(references)
    assert count.unique == 3
    assert count.duplicates_excluded == 0
    assert count.passed == 1
    assert count.failed == 2

    # 9. a restart resolves the same campaign as complete, from the Event Store alone
    campaign = RealityCampaignManifest(
        campaign_id=uuid4(),
        campaign_version=1,
        planned_runs=(baseline_identity, incomplete_identity, correct_identity),
        verifier_profile_hash=digest("c3 verifier profile"),
        created_at=utc_now(),
    )
    resume = await ledger.plan_resume(
        campaign, task_run_ids=[baseline_run, incomplete_run, correct_run]
    )
    assert resume.is_complete is True

    # 10. re-recording an identical outcome is a free no-op, not a second execution
    replay = await recorder.record(
        outcome=coding_outcome(
            task_run_id=correct_run, status=CodingOutcomeStatus.ACCEPTED, marker="correct_narrow"
        ),
        task=manifest,
        evidence=correct_evidence,
        candidate=correct_candidate,
        correlation_id=correct_run,
        run_identity=correct_identity,
    )
    assert replay.replayed is True
    assert replay.reference.source_event_id == correct.reference.source_event_id
    recorded_all, _ = await ledger.recorded_runs(
        campaign, task_run_ids=[baseline_run, incomplete_run, correct_run]
    )
    assert count_outcomes(recorded_all).unique == 3


@pytest.mark.asyncio
async def test_the_control_bundle_is_not_writable_from_inside_the_container(
    tmp_path: Path,
) -> None:
    """The hidden tests are the answer key. A container that could rewrite them owns the score."""
    sandbox = DockerSandbox(SANDBOX_IMAGE)
    task = write_task(
        "numeric_logic.empty_mean",
        root=tmp_path / "task",
        seed=1,
        hidden_bundle_artifact_id=uuid4(),
        hidden_bundle_hash=digest("placeholder"),
        created_at=utc_now(),
    )
    bundle = load_bundle(
        task_id=task.manifest.task_id,
        host_path=task.control,
        artifact_id=uuid4(),
        artifact_hash=digest("control archive"),
    )
    sandbox_id = f"cogos-readonly-{uuid4().hex[:12]}"
    try:
        result = await sandbox.run(
            SandboxRequest(
                sandbox_id=sandbox_id,
                tool_call_id=str(uuid4()),
                task_run_id=str(uuid4()),
                workspace=str(task.workspace),
                executable="python",
                arguments=(
                    "-c",
                    "from pathlib import Path\n"
                    "try:\n"
                    "    Path('/verification/test_hidden_stats.py').write_text('pass')\n"
                    "except OSError:\n"
                    "    raise SystemExit(0)\n"
                    "raise SystemExit(1)\n",
                ),
                limits=LIMITS,
                verification_input=SandboxVerificationInput(
                    host_path=str(task.control.resolve()),
                    content_hash=bundle.bundle_content_hash,
                ),
            )
        )
    finally:
        await sandbox.cleanup(sandbox_id)

    assert result.exit_code == 0, "writing to /verification must fail inside the container"
    assert (
        load_bundle(
            task_id=task.manifest.task_id,
            host_path=task.control,
            artifact_id=uuid4(),
            artifact_hash=digest("control archive"),
        ).bundle_content_hash
        == bundle.bundle_content_hash
    )
