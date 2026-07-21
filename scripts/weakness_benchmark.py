"""Run the deterministic credential-free Weakness Mining benchmark."""

from __future__ import annotations

import argparse
import asyncio
import json
from time import perf_counter

from weakness import fixture_service


async def measure(cases: int) -> dict[str, object]:
    service, request, profile = fixture_service(cases)
    started = perf_counter()
    result = await service.mine(request, profile)
    elapsed = perf_counter() - started
    if result.manifest is None:
        raise RuntimeError("weakness benchmark did not produce a manifest")
    summary = result.manifest.summary
    return {
        "cases": cases,
        "signals": summary.signal_count,
        "groups": summary.group_count,
        "weaknesses": summary.weakness_count,
        "queue_entries": summary.queue_entry_count,
        "elapsed_seconds": round(elapsed, 3),
        "provider_calls": 0,
        "source_writes": 0,
        "automatic_confirmations": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=18)
    args = parser.parse_args()
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    print(json.dumps(asyncio.run(measure(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
