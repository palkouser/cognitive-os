"""Measure a bounded CPU-only Weakness Mining scale baseline."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import tracemalloc

from weakness_benchmark import measure


async def _measure(cases: int, batches: int) -> dict[str, object]:
    tracemalloc.start()
    results = [await measure(cases) for _ in range(batches)]
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    durations = sorted(float(item["elapsed_seconds"]) for item in results)
    return {
        "cases_per_batch": cases,
        "batches": batches,
        "signals": sum(int(item["signals"]) for item in results),
        "p50_seconds": round(statistics.median(durations), 3),
        "p95_seconds": durations[max(0, int(batches * 0.95) - 1)],
        "peak_memory_bytes": peak_bytes,
        "database_bytes": None,
        "artifact_bytes": 0,
        "query_plans": "not-applicable-in-memory",
        "provider_calls": 0,
        "source_writes": 0,
        "claim": "local measurement only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=10_000)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()
    if args.cases < 1 or args.batches < 1:
        raise SystemExit("--cases and --batches must be positive")
    print(json.dumps(asyncio.run(_measure(args.cases, args.batches)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
