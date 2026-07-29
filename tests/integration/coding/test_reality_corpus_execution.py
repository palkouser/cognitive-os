"""Execute the whole Sprint 21C3 corpus against the real rootless sandbox.

Opt-in, and slow on purpose: 30 tasks by 5 variants by 2 suites is 300 container runs, plus 120
cross-task transfer attempts. Nothing cheaper can answer the two questions that matter, because
both are claims about what code *does*:

* does the published test suite pass on the broken code, and on a patch that only satisfies it?
  If not, the hidden suite is decoration and the corpus measures nothing;
* can a correction written for one task solve a sibling task? If so, the family is one problem
  with five names and a group-aware split will not save the evaluation.

Enable with `COGOS_RUN_SANDBOX_INTEGRATION=1` after `scripts/sandbox_build.sh`.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.coding.hidden_verification import (
    HiddenVerificationRunner,
    HiddenVerificationStatus,
    load_bundle,
)
from cognitive_os.coding.reality_leakage import cross_task_transfers
from cognitive_os.coding.reality_tasks import (
    _TEMPLATES,
    apply_candidate,
    available_templates,
    offline_strategies,
    write_task,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.reality import RealityCandidateStrategy, RealityStrategyFamily
from cognitive_os.domain.sandbox import SandboxLimits, SandboxRequest
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox

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


async def _visible_exit_code(sandbox: DockerSandbox, workspace: Path) -> int:
    sandbox_id = f"cogos-corpus-v-{uuid4().hex[:12]}"
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


@pytest.fixture(scope="module")
def sandbox() -> DockerSandbox:
    return DockerSandbox(SANDBOX_IMAGE)


@pytest.mark.asyncio
@pytest.mark.parametrize("template_id", available_templates())
async def test_task_satisfies_the_corpus_contract(
    template_id: str, sandbox: DockerSandbox, tmp_path: Path
) -> None:
    """The published suite passes on every variant; only the hidden suite discriminates."""
    task = write_task(
        template_id,
        root=tmp_path,
        seed=1,
        hidden_bundle_artifact_id=uuid4(),
        hidden_bundle_hash="0" * 64,
        created_at=utc_now(),
    )
    bundle = load_bundle(
        task_id=task.manifest.task_id,
        host_path=task.control,
        artifact_id=uuid4(),
        artifact_hash="0" * 64,
    )
    runner = HiddenVerificationRunner(sandbox=sandbox, limits=LIMITS, image_digest=SANDBOX_IMAGE)

    async def run(label: str, strategy: RealityCandidateStrategy | None) -> tuple[int, object]:
        workspace = tmp_path / f"run-{label}"
        shutil.copytree(task.workspace, workspace)
        if strategy is not None:
            apply_candidate(task, strategy, workspace=workspace)
        visible = await _visible_exit_code(sandbox, workspace)
        evidence = await runner.run(
            task_id=task.manifest.task_id,
            task_run_id=uuid4(),
            workspace=workspace,
            bundle=bundle,
        )
        return visible, evidence

    baseline_visible, baseline_evidence = await run("baseline", None)
    assert baseline_visible == 0, f"{template_id}: the published suite must not reveal the defect"
    assert baseline_evidence.status is HiddenVerificationStatus.FAILED  # type: ignore[attr-defined]

    for strategy in offline_strategies():
        visible, evidence = await run(strategy.value, strategy)
        assert visible == 0, f"{template_id}/{strategy.value}: the published suite must pass"
        expected = (
            HiddenVerificationStatus.PASSED
            if strategy.family is RealityStrategyFamily.CORRECT
            else HiddenVerificationStatus.FAILED
        )
        assert evidence.status is expected, (  # type: ignore[attr-defined]
            f"{template_id}/{strategy.value}: hidden verification disagrees with the "
            f"declared strategy ({evidence.reason})"  # type: ignore[attr-defined]
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("template_id", available_templates())
async def test_the_two_incorrect_candidates_fail_different_hidden_tests(
    template_id: str, sandbox: DockerSandbox, tmp_path: Path
) -> None:
    """Two candidates failing the same test are one candidate with two names."""
    task = write_task(
        template_id,
        root=tmp_path,
        seed=1,
        hidden_bundle_artifact_id=uuid4(),
        hidden_bundle_hash="0" * 64,
        created_at=utc_now(),
    )
    bundle = load_bundle(
        task_id=task.manifest.task_id,
        host_path=task.control,
        artifact_id=uuid4(),
        artifact_hash="0" * 64,
    )
    failures = {}
    for strategy in (
        RealityCandidateStrategy.INCOMPLETE_A,
        RealityCandidateStrategy.INCOMPLETE_B,
    ):
        workspace = tmp_path / f"diff-{strategy.value}"
        shutil.copytree(task.workspace, workspace)
        apply_candidate(task, strategy, workspace=workspace)
        failures[strategy] = await _failed_hidden_tests(sandbox, workspace, task, bundle)

    first = failures[RealityCandidateStrategy.INCOMPLETE_A]
    second = failures[RealityCandidateStrategy.INCOMPLETE_B]
    assert first and second, template_id
    assert first != second, f"{template_id}: both incorrect candidates fail {sorted(first)}"


async def _failed_hidden_tests(
    sandbox: DockerSandbox, workspace: Path, task: object, bundle: object
) -> set[str]:
    from cognitive_os.coding.hidden_verification import HIDDEN_PYTEST_ARGUMENTS
    from cognitive_os.domain.sandbox import SandboxVerificationInput

    sandbox_id = f"cogos-corpus-h-{uuid4().hex[:12]}"
    try:
        result = await sandbox.run(
            SandboxRequest(
                sandbox_id=sandbox_id,
                tool_call_id=str(uuid4()),
                task_run_id=str(uuid4()),
                workspace=str(workspace),
                executable="pytest",
                arguments=(*HIDDEN_PYTEST_ARGUMENTS, "-rf"),
                limits=LIMITS,
                verification_input=SandboxVerificationInput(
                    host_path=str(task.control.resolve()),  # type: ignore[attr-defined]
                    content_hash=bundle.bundle_content_hash,  # type: ignore[attr-defined]
                ),
            )
        )
    finally:
        await sandbox.cleanup(sandbox_id)
    return {
        line.split("::")[-1].split(" ")[0]
        for line in result.stdout.decode(errors="replace").splitlines()
        if line.startswith("FAILED ")
    }


@pytest.mark.asyncio
async def test_a_correction_from_a_sibling_task_solves_nothing(tmp_path: Path) -> None:
    """The universal-patch adversary, in the only form that proves anything.

    Concatenating every declared answer trivially solves the corpus, because each task's own
    answer is in the pile. What must not happen is a correction written for one task solving a
    different one — that is what a corpus of near-clones would allow.
    """
    sandbox = DockerSandbox(SANDBOX_IMAGE)
    runner = HiddenVerificationRunner(sandbox=sandbox, limits=LIMITS, image_digest=SANDBOX_IMAGE)
    tasks, bundles = {}, {}
    for template_id in available_templates():
        task = write_task(
            template_id,
            root=tmp_path / template_id.replace(".", "_"),
            seed=1,
            hidden_bundle_artifact_id=uuid4(),
            hidden_bundle_hash="0" * 64,
            created_at=utc_now(),
        )
        tasks[template_id] = task
        bundles[template_id] = load_bundle(
            task_id=task.manifest.task_id,
            host_path=task.control,
            artifact_id=uuid4(),
            artifact_hash="0" * 64,
        )

    solved = []
    transfers = cross_task_transfers(_TEMPLATES)
    for index, transfer in enumerate(transfers):
        recipient = tasks[transfer.recipient_template_id]
        workspace = tmp_path / f"transfer-{index}"
        shutil.copytree(recipient.workspace, workspace)
        (workspace / transfer.path).write_text(transfer.source, encoding="utf-8")
        evidence = await runner.run(
            task_id=recipient.manifest.task_id,
            task_run_id=uuid4(),
            workspace=workspace,
            bundle=bundles[transfer.recipient_template_id],
        )
        if evidence.passed:
            solved.append(f"{transfer.donor_template_id} -> {transfer.recipient_template_id}")
        shutil.rmtree(workspace, ignore_errors=True)
        await asyncio.sleep(0)

    assert transfers, "the adversary must actually attempt something"
    assert solved == [], f"a correction solved a task it was not written for: {solved}"
