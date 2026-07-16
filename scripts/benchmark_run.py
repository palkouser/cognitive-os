"""Run a bounded local benchmark manifest in deterministic replay mode."""

import argparse
import asyncio
import os
from pathlib import Path

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.context_adapter import context_benchmark_case
from cognitive_os.benchmarks.reporting import render_json, render_markdown
from cognitive_os.benchmarks.runner import BenchmarkRunner, CaseExecutor
from cognitive_os.benchmarks.semantic_adapter import (
    SemanticBenchmarkAdapter,
    semantic_benchmark_case,
)
from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.common import utc_now


async def replay_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    now = utc_now()
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED,
        started_at=now,
        finished_at=now,
        metrics={"expected_outcome_matched": 1.0},
    )


async def coding_replay_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    """Replay sanitized expected trajectories without credentials or repository mutation."""
    now = utc_now()
    expected = str(case.expected_outputs.get("status", "failed"))
    accepted = expected == "accepted"
    rejected = expected == "rejected"
    repair = str(case.problem_request.get("scenario")) == "repair"
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED,
        started_at=now,
        finished_at=now,
        metrics={
            "expected_outcome_matched": 1.0,
            "task_success": float(accepted),
            "accepted_diff": float(accepted),
            "patch_attempts": float(2 if repair else (0 if rejected else 1)),
            "repair_cycles": float(repair),
            "policy_denials": float(rejected),
            "main_tree_integrity": 1.0,
            "workspace_cleanup_status": 1.0,
            "sandbox_failures": 0.0,
        },
    )


async def memory_replay_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    """Replay declared governed-memory outcomes with safety metrics always present."""
    now = utc_now()
    scenario = str(case.problem_request.get("scenario"))
    denied = "rejection" in scenario or "mismatch" in scenario
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED,
        started_at=now,
        finished_at=now,
        metrics={
            "expected_outcome_matched": 1.0,
            "write_success": float(not denied),
            "policy_denials": float(denied),
            "provenance_completeness": 1.0,
            "revision_integrity": 1.0,
            "text_recall_at_k": 1.0,
            "vector_recall_at_k": 1.0,
            "mrr": 1.0,
            "scope_leaks": 0.0,
            "sensitivity_leaks": 0.0,
            "access_audit_completeness": 1.0,
        },
    )


async def _run(manifest_path: Path, output: Path, seed: int, mode: str) -> int:
    manifest = load_manifest(manifest_path)
    executor: CaseExecutor
    engine = None
    events = None
    artifacts = None
    if mode == "coding-replay":
        executor = coding_replay_case
    elif mode == "context-replay":
        executor = context_benchmark_case
    elif mode == "memory-replay":
        executor = memory_replay_case
    elif mode == "semantic-replay":
        database_url = os.environ.get("COGOS_DATABASE_URL")
        if database_url:
            from sqlalchemy import text

            from cognitive_os.events.benchmark_event_service import BenchmarkEventService
            from cognitive_os.events.catalog import build_default_event_catalog
            from cognitive_os.infrastructure.artifacts.filesystem import (
                ContentAddressedFilesystem,
            )
            from cognitive_os.infrastructure.artifacts.service import ArtifactService
            from cognitive_os.infrastructure.postgres.artifact_repository import (
                PostgresArtifactRepository,
            )
            from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
            from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
            from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
                PostgresSemanticMemoryRepository,
            )

            engine = create_postgres_engine(database_url)
            async with engine.connect() as connection:
                database_name = str(await connection.scalar(text("SELECT current_database()")))
            if not database_name.endswith("_test"):
                raise RuntimeError(
                    "semantic PostgreSQL benchmarks require an isolated _test database"
                )
            executor = SemanticBenchmarkAdapter(PostgresSemanticMemoryRepository(engine))
            events = BenchmarkEventService(
                PostgresEventStore(engine, build_default_event_catalog())
            )
            artifact_root = os.environ.get("COGOS_ARTIFACT_ROOT")
            if not artifact_root:
                raise RuntimeError(
                    "COGOS_ARTIFACT_ROOT is required for PostgreSQL semantic benchmarks"
                )
            artifacts = ArtifactService(
                ContentAddressedFilesystem(Path(artifact_root)),
                PostgresArtifactRepository(engine),
            )
        else:
            executor = semantic_benchmark_case
    else:
        executor = replay_case
    try:
        run = await BenchmarkRunner(
            executor,
            events=events,
            artifacts=artifacts,
            git_commit="local",
        ).run_manifest(manifest, random_seed=seed)
    finally:
        if engine is not None:
            await engine.dispose()
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{run.run_id}.json").write_bytes(render_json(run))
    (output / f"{run.run_id}.md").write_text(render_markdown(run), encoding="utf-8")
    print((output / f"{run.run_id}.json").as_posix())
    return 0 if run.aggregate_metrics.get("case_pass_rate") == 1 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "verifier_only",
            "controller-replay",
            "controller_mock",
            "coding-replay",
            "memory-replay",
            "semantic-replay",
            "context-replay",
        ),
        default="verifier_only",
    )
    parser.add_argument("--report-directory", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    return asyncio.run(_run(args.manifest, args.report_directory, args.seed, args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
