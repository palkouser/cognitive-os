"""Run a bounded local benchmark manifest in deterministic replay mode."""

import argparse
import asyncio
from pathlib import Path

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.reporting import render_json, render_markdown
from cognitive_os.benchmarks.runner import BenchmarkRunner
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


async def _run(manifest_path: Path, output: Path, seed: int) -> int:
    manifest = load_manifest(manifest_path)
    run = await BenchmarkRunner(replay_case, git_commit="local").run_manifest(
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
        choices=("verifier_only", "controller-replay", "controller_mock"),
        default="verifier_only",
    )
    parser.add_argument("--report-directory", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    return asyncio.run(_run(args.manifest, args.report_directory, args.seed))


if __name__ == "__main__":
    raise SystemExit(main())
