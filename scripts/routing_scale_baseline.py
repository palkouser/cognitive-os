"""Measure the bounded CPU-only in-memory routing path."""

from __future__ import annotations

import argparse
import asyncio
import json
from statistics import quantiles
from time import perf_counter

from cognitive_os.routing.fixtures import build_routing_request, replay_profiles, static_policy
from cognitive_os.routing.repository import InMemoryCapabilityRepository
from cognitive_os.routing.service import RoutingService


async def run(cases: int) -> dict[str, object]:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    for profile in replay_profiles():
        await service.register_profile(profile)
    policy = static_policy()
    await service.create_policy(policy)
    latencies = []
    started = perf_counter()
    for index in range(cases):
        case_started = perf_counter()
        await service.route_static(build_routing_request(index), policy)
        latencies.append((perf_counter() - case_started) * 1000)
    elapsed = perf_counter() - started
    percentiles = quantiles(latencies, n=20) if len(latencies) >= 20 else latencies
    return {
        "cases": cases,
        "elapsed_seconds": round(elapsed, 3),
        "p50_ms": round(sorted(latencies)[len(latencies) // 2], 3),
        "p95_ms": round(percentiles[-1], 3),
        "provider_calls": 0,
        "cpu_only": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=10_000)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error("--cases must be positive")
    print(json.dumps(asyncio.run(run(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
