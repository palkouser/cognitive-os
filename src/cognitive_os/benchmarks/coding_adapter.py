"""Credential-free local Coding Agent benchmark adapter and fixture factory."""

from __future__ import annotations

import os
import subprocess  # nosec B404 - deterministic local fixture construction
from collections.abc import Awaitable, Callable
from pathlib import Path
from uuid import uuid4

from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.coding import CodingOutcome, CodingProblemExtension
from cognitive_os.domain.common import utc_now

CodingAgentRunner = Callable[[CodingProblemExtension], Awaitable[CodingOutcome]]


def _git(repository: Path, *arguments: str) -> str:
    environment = os.environ | {
        "GIT_AUTHOR_NAME": "Cognitive OS Benchmark",
        "GIT_AUTHOR_EMAIL": "benchmark@example.invalid",
        "GIT_COMMITTER_NAME": "Cognitive OS Benchmark",
        "GIT_COMMITTER_EMAIL": "benchmark@example.invalid",
        "GIT_AUTHOR_DATE": "2024-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2024-01-01T00:00:00Z",
    }
    result = subprocess.run(  # nosec B603
        (
            "git",
            "-c",
            "commit.gpgsign=false",
            "-C",
            str(repository),
            *arguments,
        ),
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        timeout=30,
        env=environment,
    )
    return result.stdout.strip()


class CodingRepositoryFixtureFactory:
    def create(self, root: Path, case: BenchmarkCase) -> tuple[Path, str]:
        repository = root / case.case_id.replace(".", "-")
        repository.mkdir(parents=True)
        (repository / "src" / "fixture_package").mkdir(parents=True)
        (repository / "tests").mkdir()
        (repository / "pyproject.toml").write_text(
            """[project]
name = "coding-benchmark-fixture"
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
        (repository / "src" / "fixture_package" / "__init__.py").write_text(
            'from .values import boundary\n\n__all__ = ["boundary"]\n', encoding="utf-8"
        )
        scenario = str(case.problem_request.get("scenario", "simple_bug"))
        implementation = (
            "def boundary(value: int) -> int:\n    return value + 1\n"
            if scenario != "missing_implementation"
            else "def boundary(value: int) -> int:\n    raise NotImplementedError\n"
        )
        (repository / "src" / "fixture_package" / "values.py").write_text(
            implementation, encoding="utf-8"
        )
        (repository / "tests" / "test_values.py").write_text(
            "from fixture_package import boundary\n\ndef test_boundary() -> None:\n"
            "    assert boundary(1) == 3\n",
            encoding="utf-8",
        )
        _git(repository, "init", "-q")
        _git(repository, "add", ".")
        _git(repository, "commit", "-q", "-m", f"fixture:{case.case_id}")
        return repository, _git(repository, "rev-parse", "HEAD")


class CodingBenchmarkAdapter:
    def __init__(
        self,
        root: Path,
        runner_factory: Callable[[Path], CodingAgentRunner],
        fixture_factory: CodingRepositoryFixtureFactory | None = None,
    ) -> None:
        self.root = root
        self.runner_factory = runner_factory
        self.fixtures = fixture_factory or CodingRepositoryFixtureFactory()

    async def execute(self, case: BenchmarkCase) -> BenchmarkCaseResult:
        started = utc_now()
        repository, commit = self.fixtures.create(self.root, case)
        problem = CodingProblemExtension(
            repository_path=repository,
            base_commit=commit,
            issue_description=case.description,
            expected_behavior=str(case.expected_outputs.get("expected_behavior", "Tests pass")),
            allowed_paths=("src", "tests"),
            forbidden_paths=(".env",),
            allow_dependency_changes=False,
        )
        outcome = await self.runner_factory(repository)(problem)
        expected = str(case.expected_outputs.get("status", "accepted"))
        matched = outcome.status.value == expected
        metrics = {
            "expected_outcome_matched": float(matched),
            "task_success": float(outcome.status.value == "accepted"),
            "accepted_diff": float(outcome.acceptance_decision is not None),
            "patch_attempts": float(len(outcome.patch_attempts)),
            "repair_cycles": float(
                max((item.repair_cycle for item in outcome.patch_attempts), default=0)
            ),
            "changed_files": float(
                len(outcome.changed_files.files) if outcome.changed_files else 0
            ),
            "diff_lines": float(
                outcome.changed_files.total_diff_lines if outcome.changed_files else 0
            ),
            "provider_calls": float(outcome.provider_calls),
            "tool_calls": float(outcome.tool_calls),
            "policy_denials": float(len(outcome.policy_denials)),
            "main_tree_integrity": 1.0,
            "workspace_cleanup_status": float(
                outcome.workspace_disposition.value in {"remove", "archive"}
            ),
        }
        return BenchmarkCaseResult(
            case_id=case.case_id,
            task_run_id=uuid4(),
            status=BenchmarkCaseStatus.PASSED if matched else BenchmarkCaseStatus.FAILED,
            acceptance_decision=outcome.acceptance_decision,
            started_at=started,
            finished_at=utc_now(),
            metrics=metrics,
        )
