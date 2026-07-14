"""Auditable JSON/Markdown benchmark reporting and comparison."""

from __future__ import annotations

import json
from typing import Any

from cognitive_os.domain.benchmarks import BenchmarkRun

from .errors import BenchmarkComparisonError


def report_data(run: BenchmarkRun) -> dict[str, Any]:
    return {
        "run_id": str(run.run_id),
        "benchmark_id": run.benchmark_id,
        "benchmark_version": run.benchmark_version,
        "manifest_hash": run.manifest_hash,
        "git_commit": run.git_commit,
        "random_seed": run.random_seed,
        "status": run.status.value,
        "aggregate_metrics": dict(sorted(run.aggregate_metrics.items())),
        "cases": [
            {
                "case_id": item.case_id,
                "status": item.status.value,
                "metrics": dict(sorted(item.metrics.items())),
                "error_code": item.error.code if item.error else None,
            }
            for item in sorted(run.case_results, key=lambda item: item.case_id)
        ],
    }


def render_json(run: BenchmarkRun) -> bytes:
    return json.dumps(report_data(run), sort_keys=True, indent=2).encode()


def render_markdown(run: BenchmarkRun) -> str:
    data = report_data(run)
    lines = [
        f"# Benchmark report: {run.benchmark_id} {run.benchmark_version}",
        "",
        f"Status: {run.status.value}",
        "",
        "| Case | Status |",
        "|---|---|",
    ]
    lines.extend(f"| {item['case_id']} | {item['status']} |" for item in data["cases"])
    return "\n".join(lines) + "\n"


def compare_runs(baseline: BenchmarkRun, candidate: BenchmarkRun) -> dict[str, Any]:
    if (baseline.benchmark_id, baseline.benchmark_version) != (
        candidate.benchmark_id,
        candidate.benchmark_version,
    ):
        raise BenchmarkComparisonError("benchmark identities do not match")
    old = {item.case_id: item.status.value for item in baseline.case_results}
    new = {item.case_id: item.status.value for item in candidate.case_results}
    if set(old) != set(new):
        raise BenchmarkComparisonError("benchmark case sets do not match")
    return {
        "newly_passing": sorted(
            key for key in old if old[key] != "passed" and new[key] == "passed"
        ),
        "newly_failing": sorted(
            key for key in old if old[key] == "passed" and new[key] != "passed"
        ),
        "metric_delta": {
            key: candidate.aggregate_metrics.get(key, 0.0)
            - baseline.aggregate_metrics.get(key, 0.0)
            for key in sorted(set(baseline.aggregate_metrics) | set(candidate.aggregate_metrics))
        },
    }
