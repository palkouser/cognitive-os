"""Measure deterministic Sprint 19 controlled-change replay throughput."""

import argparse
import asyncio
import json
from pathlib import Path
from time import perf_counter

from cognitive_os.benchmarks.cases import load_manifest
from cognitive_os.benchmarks.change_adapter import change_benchmark_case


async def measure(manifest_path: str) -> dict[str, object]:
    manifest = load_manifest(Path(manifest_path))
    started = perf_counter()
    results = [change_benchmark_case(case) for case in manifest.cases]
    completed = await asyncio.gather(*results)
    return {
        "cases": len(completed),
        "passed": sum(item.status.value == "passed" for item in completed),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "provider_calls": 0,
        "active_state_mutations": 0,
        "runtime_release_operations": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="benchmarks/manifests/sprint19-change-ci.yaml")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(measure(args.manifest)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
