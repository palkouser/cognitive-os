from __future__ import annotations

import os
import subprocess  # nosec B404 - isolated local Git fixture
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from cognitive_os.coding.controller import CodingAgentFacade
from cognitive_os.coding.indexing import RepositoryIndexer
from cognitive_os.coding.patching import PatchService
from cognitive_os.coding.verification import CodingVerificationOutcome
from cognitive_os.coding.workspace import WorkspaceManager
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptanceDecisionType
from cognitive_os.domain.coding import (
    CodingLimits,
    CodingOutcomeStatus,
    CodingPatchPlan,
    CodingProblemExtension,
    CodingVerificationSummary,
    DependencyChangePolicy,
    PatchProposal,
    PathPolicy,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.infrastructure.repository.git_commands import GitCommandRunner
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService
from cognitive_os.tools.registry import ToolRegistry


def git(repository: Path, *arguments: str) -> str:
    environment = os.environ | {
        "GIT_AUTHOR_NAME": "Coding Test",
        "GIT_AUTHOR_EMAIL": "coding@example.invalid",
        "GIT_COMMITTER_NAME": "Coding Test",
        "GIT_COMMITTER_EMAIL": "coding@example.invalid",
    }
    result = subprocess.run(  # nosec B603
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env=environment,
    )
    return result.stdout.strip()


class ReplayCodingProvider:
    def __init__(self) -> None:
        self.plan_value = CodingPatchPlan(
            summary="Correct the deterministic value.",
            target_files=("src/fixture/value.py",),
            intended_changes=("Return two instead of one.",),
            tests_to_run=(("pytest", "-q"),),
        )

    async def plan(self, *_args, **_kwargs) -> CodingPatchPlan:
        return self.plan_value

    async def propose(self, *_args, workspace_revision: int, **_kwargs) -> PatchProposal:
        return PatchProposal(
            expected_workspace_revision=workspace_revision,
            plan_hash=self.plan_value.canonical_hash(),
            unified_diff="""diff --git a/src/fixture/value.py b/src/fixture/value.py
--- a/src/fixture/value.py
+++ b/src/fixture/value.py
@@ -1,2 +1,2 @@
 def value() -> int:
-    return 1
+    return 2
""",
            target_files=("src/fixture/value.py",),
            rationale="Apply the replay fixture correction.",
        )


class DirectToolExecution:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    async def execute(self, invocation, context):
        return await self.registry.require(invocation.tool_id, invocation.tool_version).execute(
            invocation, context
        )


class AcceptedVerifierBundle:
    async def verify(self, *, task_run_id: UUID, **_kwargs) -> CodingVerificationOutcome:
        return CodingVerificationOutcome(
            summary=CodingVerificationSummary(
                registry_snapshot_hash="a" * 64,
                required_criteria_resolved=True,
            ),
            decision=AcceptanceDecision(
                decision_id=uuid4(),
                task_run_id=task_run_id,
                policy_id=uuid4(),
                policy_version="1",
                decision=AcceptanceDecisionType.ACCEPTED,
                criterion_evaluations=(),
                required_passed=True,
                optional_score=1,
                reason="All deterministic fixture checks passed.",
                created_at=utc_now(),
            ),
        )


class RecordedEvents:
    def __init__(self) -> None:
        self.values: list[object] = []

    async def append(self, _task_run_id, payload, **_kwargs):
        self.values.append(payload)
        return uuid4()


@pytest.mark.asyncio
async def test_facade_accepts_patch_without_mutating_main_checkout(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "src" / "fixture").mkdir(parents=True)
    (repository / "tests").mkdir()
    (repository / "pyproject.toml").write_text(
        """[project]
name = "fixture"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["pytest>=9", "ruff>=0.12", "mypy>=1.16"]
[tool.pytest.ini_options]
testpaths = ["tests"]
[tool.ruff]
line-length = 100
[tool.mypy]
strict = true
""",
        encoding="utf-8",
    )
    source = repository / "src" / "fixture" / "value.py"
    source.write_text("def value() -> int:\n    return 1\n", encoding="utf-8")
    git(repository, "init", "-q")
    git(repository, "add", ".")
    git(repository, "commit", "-q", "-m", "fixture")
    commit = git(repository, "rev-parse", "HEAD")
    repositories = GitRepositoryService((tmp_path,), GitCommandRunner())
    limits = CodingLimits()
    workspaces = WorkspaceManager(
        tmp_path / "worktrees", tmp_path / "archives", repositories, limits
    )
    patches = PatchService(
        workspaces,
        limits,
        PathPolicy(allowed_paths=("src", "tests")),
        DependencyChangePolicy(),
    )
    registry = ToolRegistry()
    events = RecordedEvents()
    facade = CodingAgentFacade(
        repositories=repositories,
        workspaces=workspaces,
        indexer=RepositoryIndexer(limits),
        patches=patches,
        provider=ReplayCodingProvider(),  # type: ignore[arg-type]
        verifier_bundle=AcceptedVerifierBundle(),  # type: ignore[arg-type]
        tool_registry=registry,
        tool_execution=DirectToolExecution(registry),  # type: ignore[arg-type]
        events=events,  # type: ignore[arg-type]
        limits=limits,
        rootless_docker=True,
    )
    outcome = await facade.run(
        uuid4(),
        CodingProblemExtension(
            repository_path=repository,
            base_commit=commit,
            issue_description="Return the expected deterministic value.",
            expected_behavior="value() returns two.",
            allowed_paths=("src", "tests"),
        ),
    )

    assert outcome.status is CodingOutcomeStatus.ACCEPTED, (
        [item.message for item in outcome.risks],
        [type(item).__name__ for item in events.values],
    )
    assert len(outcome.patch_attempts) == 1
    assert source.read_text(encoding="utf-8").endswith("return 1\n")
    assert git(repository, "status", "--porcelain") == ""
    assert any((tmp_path / "archives").glob("*/unified-diff.patch"))
    assert len(events.values) == 8
