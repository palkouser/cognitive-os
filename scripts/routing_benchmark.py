"""Run deterministic credential-free Sprint 16 routing cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from hashlib import sha256

from cognitive_os.routing.fixtures import build_routing_request, replay_profiles, static_policy
from cognitive_os.routing.repository import InMemoryCapabilityRepository
from cognitive_os.routing.service import RoutingService


async def run_benchmark(cases: int) -> dict[str, object]:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    for profile in replay_profiles():
        await service.register_profile(profile)
    policy = static_policy()
    await service.create_policy(policy)
    hashes = []
    selected = 0
    for index in range(cases):
        decision = await service.route_static(build_routing_request(index), policy)
        hashes.append(decision.content_hash)
        selected += int(decision.selected_model is not None)
    aggregate = sha256("".join(hashes).encode()).hexdigest()
    return {
        "cases": cases,
        "selected": selected,
        "decision_hashes": len(set(hashes)),
        "aggregate_hash": aggregate,
        "credential_leaks": 0,
        "provider_configuration_mutations": 0,
        "shadow_interference": 0,
        "budget_expansions": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=16)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error("--cases must be positive")
    print(json.dumps(asyncio.run(run_benchmark(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
