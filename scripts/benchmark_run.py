"""Run a bounded local benchmark manifest in deterministic replay mode."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.reporting import render_json, render_markdown
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.benchmarks.semantic_adapter import semantic_benchmark_case
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
    if mode == "coding-replay":
        executor = coding_replay_case
    elif mode == "memory-replay":
        executor = memory_replay_case
    elif mode == "semantic-replay":
        executor = semantic_benchmark_case
    else:
        executor = replay_case
    run = await BenchmarkRunner(executor, git_commit="local").run_manifest(
        manifest, random_seed=seed
    )
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
        ),
        default="verifier_only",
    )
    parser.add_argument("--report-directory", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    return asyncio.run(_run(args.manifest, args.report_directory, args.seed, args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
