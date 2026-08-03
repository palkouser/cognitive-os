"""S21C3-031: the campaign loop's own rules, without a container.

Whether a candidate really fails the hidden suite is a question for Docker, and
`tests/integration/coding/` asks it. What is asked here is what the runner itself decides:
that a completed run is skipped rather than executed again, that a run which mutated its own
source is refused, and that the patch bytes a candidate names are actually stored.
"""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.application.services.reality_campaign_runner import (
    RealityCampaignRunner,
    WorkspaceIntegrityError,
)
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_candidates import candidate_id_for
from cognitive_os.coding.reality_tasks import available_templates, d2_templates
from cognitive_os.domain.reality import RealityCandidateStrategy, RealityRunKind
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.memory_store import MemoryEventStore

from .reality_fixtures import (
    FIXTURE_TIME,
    SANDBOX_LIMITS,
    InMemoryArtifactStore,
    StubSandbox,
)

TEMPLATE_ID = available_templates()[0]
D2_TEMPLATE_ID = d2_templates()[0]
STRATEGIES = (RealityCandidateStrategy.INCOMPLETE_A, RealityCandidateStrategy.CORRECT_NARROW)


class _CorpusShapedSandbox(StubSandbox):
    """Answers the way the corpus contract says a real sandbox would.

    Not a claim that the sandbox behaves this way — `tests/integration/coding/` proves that
    with containers. It exists because `RealityOutcomeReference` refuses a baseline that
    passed and a correct candidate that failed, so a stub returning one exit code for
    everything cannot produce a recordable run at all.
    """

    async def run(self, request):  # type: ignore[no-untyped-def]
        hidden = request.verification_input is not None
        correct = "correct" in Path(request.workspace).name
        self.exit_code = 0 if correct or not hidden else 1
        return await super().run(request)


def _runner(sandbox: StubSandbox, artifacts: InMemoryArtifactStore) -> RealityCampaignRunner:
    events = MemoryEventStore()
    return RealityCampaignRunner(
        sandbox=sandbox,
        artifacts=artifacts,
        recorder=CodingOutcomeRecorder(artifacts, CodingEventService(events), events),
        harvester=None,
        limits=SANDBOX_LIMITS,
        image_digest="sha256:fixture",
        verifier_profile_hash="c" * 64,
    )


@pytest.mark.asyncio
async def test_a_completed_run_is_skipped_rather_than_executed_again(tmp_path: Path) -> None:
    """Resume costs nothing. A campaign that re-ran finished work would pay for the crash twice."""
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)

    first = await runner.run_task(
        TEMPLATE_ID,
        root=tmp_path / "first",
        strategies=STRATEGIES,
        generated_at=FIXTURE_TIME,
    )
    containers = len(sandbox.requests)
    assert containers > 0

    completed = {item.identity.key: item.step.reference for item in first.all_runs}
    second = await runner.run_task(
        TEMPLATE_ID,
        root=tmp_path / "second",
        strategies=STRATEGIES,
        generated_at=FIXTURE_TIME,
        completed=completed,
        bundle_artifact=await artifacts.describe(first.bundle_artifact_id),  # type: ignore[arg-type]
    )

    assert len(sandbox.requests) == containers, "a resumed run must not start a container"
    assert all(item.replayed for item in second.all_runs)
    assert [item.step.reference.task_run_id for item in second.all_runs] == [
        item.step.reference.task_run_id for item in first.all_runs
    ]


@pytest.mark.asyncio
async def test_a_task_generated_twice_is_the_same_task(tmp_path: Path) -> None:
    """The manifest hash binds outcomes to a task; a clock in it would break every join."""
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)

    first = await runner.run_task(
        TEMPLATE_ID, root=tmp_path / "a", strategies=(), generated_at=FIXTURE_TIME
    )
    second = await runner.run_task(
        TEMPLATE_ID,
        root=tmp_path / "b",
        strategies=(),
        generated_at=FIXTURE_TIME,
        bundle_artifact=await artifacts.describe(first.bundle_artifact_id),  # type: ignore[arg-type]
    )

    assert first.task.manifest.content_hash == second.task.manifest.content_hash
    assert first.baseline is not None
    assert second.baseline is not None
    assert first.baseline.identity.key == second.baseline.identity.key


@pytest.mark.asyncio
async def test_a_run_that_changed_the_pristine_workspace_is_refused(tmp_path: Path) -> None:
    """A campaign that patched its own source would repair later tasks with earlier fixes."""
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)
    original = RealityCampaignRunner._require_untouched

    def tamper(prepared, *, label):  # type: ignore[no-untyped-def]
        workspace = prepared.generated.workspace
        (workspace / "src" / "smuggled.py").write_text("x = 1\n", encoding="utf-8")
        original(prepared, label=label)

    RealityCampaignRunner._require_untouched = staticmethod(tamper)  # type: ignore[method-assign]
    try:
        with pytest.raises(WorkspaceIntegrityError, match="pristine workspace changed"):
            await runner.run_task(
                TEMPLATE_ID, root=tmp_path, strategies=(), generated_at=FIXTURE_TIME
            )
    finally:
        RealityCampaignRunner._require_untouched = staticmethod(original)  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_every_candidate_run_stores_the_patch_it_names(tmp_path: Path) -> None:
    """The trajectory plane reads these bytes back by hash; a named-but-absent patch fails it."""
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)

    runs = await runner.run_task(
        TEMPLATE_ID, root=tmp_path, strategies=STRATEGIES, generated_at=FIXTURE_TIME
    )

    for strategy in STRATEGIES:
        run = runs.by_strategy(strategy)
        assert run is not None
        candidate = run.step.candidate
        assert candidate is not None
        stored = await artifacts.get_bytes(candidate.patch_artifact_id)
        assert stored.decode().startswith("diff --git ")
        assert await artifacts.verify(candidate.patch_artifact_id)


@pytest.mark.asyncio
async def test_the_baseline_run_carries_no_candidate(tmp_path: Path) -> None:
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runs = await _runner(sandbox, artifacts).run_task(
        TEMPLATE_ID, root=tmp_path, strategies=(), generated_at=FIXTURE_TIME
    )

    assert runs.baseline is not None
    assert runs.baseline.identity.run_kind is RealityRunKind.BASELINE
    assert runs.baseline.step.candidate is None
    assert runs.baseline.identity.candidate_id is None


@pytest.mark.asyncio
async def test_the_recorded_control_bundle_is_what_makes_a_resume_a_resume(
    tmp_path: Path,
) -> None:
    """W4-F2. The bundle artifact reaches the run identity through the task manifest.

    `RealityTaskManifest` names its control bundle by artifact ID, the Artifact Store mints a
    fresh row for identical bytes, and `RealityRunIdentity` hashes the manifest. So a resume
    that lets `prepare_task` mint a new bundle produces a new identity for every run, matches
    nothing, and silently re-executes the whole campaign while reporting a resume. The Sprint
    21D2 self-play command did exactly that on its first resume and paid three hundred
    containers to find out.
    """
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)

    first = await runner.prepare_task(TEMPLATE_ID, root=tmp_path / "a", generated_at=FIXTURE_TIME)
    reused = await runner.prepare_task(
        TEMPLATE_ID,
        root=tmp_path / "b",
        generated_at=FIXTURE_TIME,
        bundle_artifact=first.bundle_artifact,
    )
    reminted = await runner.prepare_task(
        TEMPLATE_ID, root=tmp_path / "c", generated_at=FIXTURE_TIME
    )

    assert reused.generated.manifest.content_hash == first.generated.manifest.content_hash
    assert reminted.generated.manifest.content_hash != first.generated.manifest.content_hash


@pytest.mark.asyncio
async def test_a_d2_candidate_records_the_identity_the_seal_named(tmp_path: Path) -> None:
    """The sealed catalogue names candidates by position before anything runs.

    Re-deriving one from the recipe here would put C3's reversible encoding back on top of the
    opaque identity the seal committed to, which is the whole reason the opaque one exists.
    """
    sandbox, artifacts = _CorpusShapedSandbox(), InMemoryArtifactStore()
    runner = _runner(sandbox, artifacts)
    sealed = uuid5(NAMESPACE_URL, "cognitive-os:test:sealed-candidate")

    prepared = await runner.prepare_task(D2_TEMPLATE_ID, root=tmp_path, generated_at=FIXTURE_TIME)
    executed = await runner.run_candidate(
        prepared, RealityCandidateStrategy.RECIPE_ALPHA, candidate_id=sealed
    )

    assert executed.identity.candidate_id == sealed
    assert executed.identity.strategy is RealityCandidateStrategy.RECIPE_ALPHA
    assert executed.identity.candidate_id != candidate_id_for(
        prepared.generated.manifest.task_id, RealityCandidateStrategy.RECIPE_ALPHA
    )
