"""Credential-free Sprint 8 coding contracts, profile, and benchmark smoke path."""

from __future__ import annotations

import asyncio
import json
import subprocess  # nosec B404 - fixed local Git inspection
from pathlib import Path

from benchmark_run import coding_replay_case

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.runner import BenchmarkRunner
from cognitive_os.coding.diff import parse_unified_diff
from cognitive_os.coding.repository_profile import detect_repository_profile


async def run() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    profile = detect_repository_profile(root, rootless_docker=True)
    commit = subprocess.run(  # nosec B603
        ("git", "-C", str(root), "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    parsed = parse_unified_diff(
        """diff --git a/src/example.py b/src/example.py
--- a/src/example.py
+++ b/src/example.py
@@ -1 +1 @@
-VALUE = 1
+VALUE = 2
"""
    )
    manifest = load_manifest(root / "benchmarks/manifests/sprint8-coding-ci.yaml")
    benchmark = await BenchmarkRunner(coding_replay_case, git_commit=commit).run_manifest(
        manifest, random_seed=8
    )
    passed = (
        profile.status.value == "supported"
        and len(parsed) == 1
        and len(benchmark.case_results) == 4
        and benchmark.aggregate_metrics["case_pass_rate"] == 1
        and benchmark.aggregate_metrics["main_tree_integrity"] == len(benchmark.case_results)
    )
    return {
        "profile": profile.status.value,
        "base_commit": commit,
        "parsed_patch_files": len(parsed),
        "benchmark_cases": len(benchmark.case_results),
        "benchmark_pass_rate": benchmark.aggregate_metrics["case_pass_rate"],
        "main_tree_integrity": benchmark.aggregate_metrics["main_tree_integrity"],
        "credentials_required": False,
        "passed": passed,
    }


def main() -> int:
    result = asyncio.run(run())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
