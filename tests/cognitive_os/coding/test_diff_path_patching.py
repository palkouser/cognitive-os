from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.coding.diff import DiffPolicyError, apply_file_patch, parse_unified_diff
from cognitive_os.coding.patching import PatchService
from cognitive_os.domain.coding import (
    CodingLimits,
    DependencyChangePolicy,
    PatchProposal,
    PathPolicy,
    WorkspaceDescriptor,
    WorkspaceState,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.tools import ToolExecutionContext, ToolInvocation
from cognitive_os.tools.workspace import WorkspaceTool

MODIFY = """diff --git a/src/value.py b/src/value.py
--- a/src/value.py
+++ b/src/value.py
@@ -1,2 +1,2 @@
 def value():
-    return 1
+    return 2
"""


class FakeWorkspaces:
    def __init__(self, root: Path):
        self.root = root

    def path_for(self, _descriptor: WorkspaceDescriptor) -> Path:
        return self.root


def descriptor() -> WorkspaceDescriptor:
    task = uuid4()
    return WorkspaceDescriptor(
        workspace_id=uuid4(),
        task_run_id=task,
        base_commit="c" * 40,
        workspace_revision=0,
        state=WorkspaceState.ACTIVE,
        logical_name=f"coding-{task}",
        created_at=utc_now(),
    )


def test_unified_diff_parser_applies_exact_context() -> None:
    patch = parse_unified_diff(MODIFY)[0]
    assert apply_file_patch(b"def value():\n    return 1\n", patch) == (
        b"def value():\n    return 2\n"
    )
    with pytest.raises(DiffPolicyError, match="context"):
        apply_file_patch(b"def value():\n    return 3\n", patch)


@pytest.mark.parametrize(
    "value",
    [
        (
            "diff --git a/.git/config b/.git/config\n--- a/.git/config\n"
            "+++ b/.git/config\n@@ -1 +1 @@\n-a\n+b\n"
        ),
        "diff --git a/a b/a\nold mode 100644\nnew mode 100755\n",
        "GIT binary patch\nliteral 0\n",
        "diff --git a/../x b/../x\n--- a/../x\n+++ b/../x\n@@ -1 +1 @@\n-a\n+b\n",
    ],
)
def test_adversarial_diff_is_rejected(value: str) -> None:
    with pytest.raises((DiffPolicyError, ValueError)):
        parse_unified_diff(value)


@pytest.mark.asyncio
async def test_patch_service_applies_atomically_and_rejects_dependency_change(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "value.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    workspace = descriptor()
    service = PatchService(
        FakeWorkspaces(tmp_path),  # type: ignore[arg-type]
        CodingLimits(),
        PathPolicy(allowed_paths=("src",)),
        DependencyChangePolicy(),
    )
    proposal = PatchProposal(
        expected_workspace_revision=0,
        plan_hash="d" * 64,
        unified_diff=MODIFY,
        target_files=("src/value.py",),
        rationale="Fix the value.",
    )
    result = await service.apply(workspace, proposal)
    assert result.applied
    assert target.read_text(encoding="utf-8").endswith("return 2\n")
    repeated = await service.apply(workspace, proposal)
    assert repeated.reason_code == "repeated_patch"


@pytest.mark.asyncio
async def test_failed_multi_file_patch_leaves_every_file_unchanged(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    first = tmp_path / "src" / "a.py"
    second = tmp_path / "src" / "b.py"
    first.write_text("a = 1\n", encoding="utf-8")
    second.write_text("b = 1\n", encoding="utf-8")
    diff = """diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-a = 1
+a = 2
diff --git a/src/b.py b/src/b.py
--- a/src/b.py
+++ b/src/b.py
@@ -1 +1 @@
-b = 9
+b = 2
"""
    service = PatchService(
        FakeWorkspaces(tmp_path),  # type: ignore[arg-type]
        CodingLimits(),
        PathPolicy(allowed_paths=("src",)),
        DependencyChangePolicy(),
    )
    result = await service.apply(
        descriptor(),
        PatchProposal(
            expected_workspace_revision=0,
            plan_hash="e" * 64,
            unified_diff=diff,
            target_files=("src/a.py", "src/b.py"),
            rationale="Attempt invalid multi-file change.",
        ),
    )
    assert not result.applied
    assert first.read_text(encoding="utf-8") == "a = 1\n"
    assert second.read_text(encoding="utf-8") == "b = 1\n"


@pytest.mark.asyncio
async def test_workspace_patch_tool_advances_its_sealed_revision(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "value.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    workspace = descriptor()
    workspaces = FakeWorkspaces(tmp_path)
    patches = PatchService(
        workspaces,  # type: ignore[arg-type]
        CodingLimits(),
        PathPolicy(allowed_paths=("src",)),
        DependencyChangePolicy(),
    )

    class FakeRepositories:
        async def diff(self, _path: Path, _commit: str) -> str:
            return ""

    tool = WorkspaceTool(
        "apply_patch",
        workspace,
        workspaces,  # type: ignore[arg-type]
        patches,
        FakeRepositories(),  # type: ignore[arg-type]
    )
    context = ToolExecutionContext(
        workspace="logical",
        timeout_seconds=10,
        maximum_stdout_bytes=10_000,
        maximum_stderr_bytes=10_000,
        maximum_artifact_bytes=10_000,
    )
    first = PatchProposal(
        expected_workspace_revision=0,
        plan_hash="1" * 64,
        unified_diff=MODIFY,
        target_files=("src/value.py",),
        rationale="First repair step.",
    )
    second = PatchProposal(
        expected_workspace_revision=1,
        plan_hash="2" * 64,
        unified_diff=MODIFY.replace("-    return 1", "-    return 2").replace(
            "+    return 2", "+    return 3"
        ),
        target_files=("src/value.py",),
        rationale="Second repair step.",
    )
    for proposal in (first, second):
        invocation = ToolInvocation(
            tool_call_id=uuid4(),
            task_run_id=workspace.task_run_id,
            correlation_id=uuid4(),
            tool_id="workspace.apply_patch",
            tool_version="1",
            arguments=proposal.model_dump(mode="json"),
            requested_at=utc_now(),
            requested_by="test",
        )
        result = await tool.execute(invocation, context)
        assert result.result["applied"] is True  # type: ignore[index]
    assert target.read_text(encoding="utf-8").endswith("return 3\n")


@pytest.mark.asyncio
async def test_file_writer_requires_baseline_hash_and_counts_aggregate_lines(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    target = tmp_path / "src" / "value.py"
    target.write_text("VALUE = 1\n", encoding="utf-8")
    service = PatchService(
        FakeWorkspaces(tmp_path),  # type: ignore[arg-type]
        CodingLimits(maximum_diff_lines=2),
        PathPolicy(allowed_paths=("src",)),
        DependencyChangePolicy(),
    )
    workspace = descriptor()
    with pytest.raises(DiffPolicyError, match="expected content hash"):
        await service.write_file(workspace, "src/value.py", b"VALUE = 2\n")
    await service.write_file(
        workspace,
        "src/value.py",
        b"VALUE = 2\n",
        expected_before_hash=sha256(b"VALUE = 1\n").hexdigest(),
    )
    with pytest.raises(DiffPolicyError, match="cumulative diff line"):
        await service.write_file(
            workspace,
            "src/value.py",
            b"VALUE = 3\n",
            expected_before_hash=sha256(b"VALUE = 2\n").hexdigest(),
        )
