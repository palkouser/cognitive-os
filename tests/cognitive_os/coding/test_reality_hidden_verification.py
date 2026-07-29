"""S21C3-021 and S21C3-022: the control mount, and what the criterion does with its evidence.

These tests never launch a container. What they assert is what `DockerSandbox` *would* be
asked to do, and what the criterion concludes from a normalized result. The opt-in test in
`tests/integration/coding/test_reality_vertical_slice.py` is what proves a real read-only
mount and a real hidden failure.
"""

from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.coding.hidden_verification import (
    HIDDEN_PYTEST_ARGUMENTS,
    HIDDEN_PYTEST_VERIFIER_ID,
    HiddenVerificationBundle,
    HiddenVerificationRunner,
    HiddenVerificationStatus,
    load_bundle,
)
from cognitive_os.coding.verification import CodingVerifierBundleFactory
from cognitive_os.domain.coding import CodingLimits
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.sandbox import SandboxRequest, SandboxVerificationInput
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.providers.workspace_snapshot import snapshot_workspace
from cognitive_os.tools.errors import SandboxExecutionError
from cognitive_os.tools.sandbox.lifecycle import DockerSandbox
from cognitive_os.tools.sandbox.tools import SandboxDevelopmentTool
from cognitive_os.verification.coding.hidden_pytest import HiddenPytestVerifier

from .reality_fixtures import (
    FIXTURE_TIME,
    SANDBOX_LIMITS,
    StubSandbox,
    digest,
    hidden_evidence,
    task_manifest,
)


def _bundle_on_disk(root: Path) -> HiddenVerificationBundle:
    control = root / "control"
    control.mkdir(parents=True, exist_ok=True)
    (control / "test_hidden.py").write_text("def test_hidden() -> None:\n    assert True\n")
    return load_bundle(
        task_id=uuid4(),
        host_path=control,
        artifact_id=uuid4(),
        artifact_hash=digest("archive"),
    )


def test_the_control_mount_has_no_writable_or_relocatable_variant() -> None:
    """`container_path` is a Literal, so widening it is a contract change, not a setting."""
    with pytest.raises(ValueError):
        SandboxVerificationInput(
            host_path="/tmp/control",
            container_path="/workspace",  # type: ignore[arg-type]
            content_hash=digest("bundle"),
        )


def test_the_control_mount_refuses_a_relative_host_path() -> None:
    with pytest.raises(ValueError, match="absolute and non-traversing"):
        SandboxVerificationInput(host_path="control", content_hash=digest("bundle"))


def test_the_hidden_command_is_fixed_and_names_only_the_control_mount() -> None:
    assert "/verification" in HIDDEN_PYTEST_ARGUMENTS
    assert not any(item.startswith("/workspace") for item in HIDDEN_PYTEST_ARGUMENTS)
    assert "-k" not in HIDDEN_PYTEST_ARGUMENTS


def test_provider_visible_sandbox_tools_cannot_carry_a_control_mount() -> None:
    """The hidden path is not the tool plane, so a provider-visible descriptor cannot reach it."""
    tool = SandboxDevelopmentTool("pytest", DockerSandbox("image"), SANDBOX_LIMITS)

    assert tool.descriptor.provider_visible is True
    assert "verification_input" not in tool.descriptor.input_schema["properties"]  # type: ignore[index]


@pytest.mark.asyncio
async def test_runner_mounts_the_bundle_read_only_at_the_fixed_destination(
    tmp_path: Path,
) -> None:
    bundle = _bundle_on_disk(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sandbox = StubSandbox(exit_code=0)
    runner = HiddenVerificationRunner(
        sandbox=sandbox,  # type: ignore[arg-type]
        limits=SANDBOX_LIMITS,
        image_digest="sha256:fixture",
    )

    evidence = await runner.run(
        task_id=bundle.task_id, task_run_id=uuid4(), workspace=workspace, bundle=bundle
    )

    request: SandboxRequest = sandbox.requests[0]
    assert request.verification_input is not None
    assert request.verification_input.container_path == "/verification"
    assert request.verification_input.content_hash == bundle.bundle_content_hash
    assert request.arguments == HIDDEN_PYTEST_ARGUMENTS
    assert evidence.status is HiddenVerificationStatus.PASSED
    assert sandbox.cleaned == [request.sandbox_id]


@pytest.mark.asyncio
async def test_a_tampered_bundle_is_unverifiable_before_anything_runs(tmp_path: Path) -> None:
    bundle = _bundle_on_disk(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "control" / "test_hidden.py").write_text("def test_hidden():\n    assert True\n")
    sandbox = StubSandbox()
    runner = HiddenVerificationRunner(
        sandbox=sandbox,  # type: ignore[arg-type]
        limits=SANDBOX_LIMITS,
        image_digest="sha256:fixture",
    )

    evidence = await runner.run(
        task_id=bundle.task_id, task_run_id=uuid4(), workspace=workspace, bundle=bundle
    )

    assert evidence.status is HiddenVerificationStatus.UNVERIFIABLE
    assert evidence.reason == "control bundle content hash changed"
    assert sandbox.requests == []


@pytest.mark.asyncio
async def test_a_missing_bundle_is_unverifiable_rather_than_failed(tmp_path: Path) -> None:
    bundle = _bundle_on_disk(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for item in (tmp_path / "control").iterdir():
        item.unlink()
    (tmp_path / "control").rmdir()
    runner = HiddenVerificationRunner(
        sandbox=StubSandbox(),  # type: ignore[arg-type]
        limits=SANDBOX_LIMITS,
        image_digest="sha256:fixture",
    )

    evidence = await runner.run(
        task_id=bundle.task_id, task_run_id=uuid4(), workspace=workspace, bundle=bundle
    )

    assert evidence.status is HiddenVerificationStatus.UNVERIFIABLE
    assert evidence.passed is False


def test_docker_sandbox_refuses_a_bundle_whose_bytes_changed(tmp_path: Path) -> None:
    control = tmp_path / "control"
    control.mkdir()
    (control / "test_hidden.py").write_text("def test_hidden():\n    assert True\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = SandboxRequest(
        sandbox_id="cogos-test",
        tool_call_id=str(uuid4()),
        task_run_id=str(uuid4()),
        workspace=str(workspace),
        executable="pytest",
        arguments=HIDDEN_PYTEST_ARGUMENTS,
        limits=SANDBOX_LIMITS,
        verification_input=SandboxVerificationInput(
            host_path=str(control), content_hash=digest("a bundle that is not this one")
        ),
    )

    with pytest.raises(SandboxExecutionError, match="declared content hash"):
        DockerSandbox("image")._verification_mount(request)


def test_docker_sandbox_builds_a_read_only_mount_for_a_matching_bundle(tmp_path: Path) -> None:
    control = tmp_path / "control"
    control.mkdir()
    (control / "test_hidden.py").write_text("def test_hidden():\n    assert True\n")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = SandboxRequest(
        sandbox_id="cogos-test",
        tool_call_id=str(uuid4()),
        task_run_id=str(uuid4()),
        workspace=str(workspace),
        executable="pytest",
        arguments=HIDDEN_PYTEST_ARGUMENTS,
        limits=SANDBOX_LIMITS,
        verification_input=SandboxVerificationInput(
            host_path=str(control), content_hash=snapshot_workspace(control).digest
        ),
    )

    mount = DockerSandbox("image")._verification_mount(request)

    assert mount[0] == "--mount"
    assert mount[1].endswith(",dst=/verification,readonly")


def test_a_request_without_a_control_mount_is_unchanged(tmp_path: Path) -> None:
    """Every pre-C3 caller keeps the mount vector it had."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    request = SandboxRequest(
        sandbox_id="cogos-test",
        tool_call_id=str(uuid4()),
        task_run_id=str(uuid4()),
        workspace=str(workspace),
        executable="pytest",
        arguments=("-q",),
        limits=SANDBOX_LIMITS,
    )

    assert DockerSandbox("image")._verification_mount(request) == ()


@pytest.mark.parametrize(
    ("status", "expected"),
    (
        (HiddenVerificationStatus.PASSED, VerifierStatus.PASSED),
        (HiddenVerificationStatus.FAILED, VerifierStatus.FAILED),
        (HiddenVerificationStatus.TIMED_OUT, VerifierStatus.FAILED),
        (HiddenVerificationStatus.UNVERIFIABLE, VerifierStatus.UNVERIFIABLE),
    ),
)
@pytest.mark.asyncio
async def test_the_criterion_never_turns_an_unmeasured_run_into_a_failure(
    status: HiddenVerificationStatus, expected: VerifierStatus
) -> None:
    task = task_manifest()
    evidence = hidden_evidence(task=task, task_run_id=uuid4(), status=status)
    result = await HiddenPytestVerifier().verify(
        VerificationRequest(
            verification_id=uuid4(),
            task_run_id=uuid4(),
            criterion_id=uuid5(NAMESPACE_URL, "criterion:coding.hidden_pytest"),
            verifier_id=HIDDEN_PYTEST_VERIFIER_ID,
            verifier_version="1",
            subject=VerificationSubject(
                subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                inline_value=evidence.as_verifier_subject(),
            ),
            configuration={},
            requested_at=FIXTURE_TIME,
            correlation_id=uuid4(),
        )
    )

    assert result.status is expected


@pytest.mark.asyncio
async def test_the_criterion_errors_on_evidence_it_cannot_trust() -> None:
    result = await HiddenPytestVerifier().verify(
        VerificationRequest(
            verification_id=uuid4(),
            task_run_id=uuid4(),
            criterion_id=uuid5(NAMESPACE_URL, "criterion:coding.hidden_pytest"),
            verifier_id=HIDDEN_PYTEST_VERIFIER_ID,
            verifier_version="1",
            subject=VerificationSubject(
                subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                inline_value={"criterion_id": "coding.hidden_pytest", "status": "passed"},
            ),
            configuration={},
            requested_at=FIXTURE_TIME,
            correlation_id=uuid4(),
        )
    )

    assert result.status is VerifierStatus.ERROR


def test_hidden_evidence_never_carries_captured_output() -> None:
    """A hidden assertion message names the edge case it checks."""
    task = task_manifest()
    evidence = hidden_evidence(task=task, task_run_id=uuid4())
    subject = evidence.as_verifier_subject()

    assert "stdout" not in subject
    assert "stderr" not in subject
    assert set(subject) == {
        "criterion_id",
        "status",
        "exit_code",
        "bundle_content_hash",
        "sandbox_image_digest",
        "evidence_hash",
    }


def test_the_hidden_criterion_is_absent_from_the_pre_c3_acceptance_profile() -> None:
    factory = CodingVerifierBundleFactory(
        registry=None,  # type: ignore[arg-type]
        verification=None,  # type: ignore[arg-type]
        acceptance=AcceptancePolicyService(),
        limits=CodingLimits(),
    )

    visible = factory.policy()
    hidden = factory.policy(hidden_verification=True)
    visible_ids = {item.verifier_id for item in visible.requirements}
    hidden_ids = {item.verifier_id for item in hidden.requirements}

    assert HIDDEN_PYTEST_VERIFIER_ID not in visible_ids
    assert HIDDEN_PYTEST_VERIFIER_ID in hidden_ids
    assert visible_ids < hidden_ids
    assert visible.policy_id != hidden.policy_id
