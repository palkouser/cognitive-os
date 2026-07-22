"""Measure the deterministic credential-free proposal path."""

import argparse
import asyncio
import json
from time import perf_counter

from proposal import create_fixture, fixture_service

from cognitive_os.domain.proposals import HarnessProposalType


async def measure(cases: int) -> dict[str, object]:
    started = perf_counter()
    types = tuple(HarnessProposalType)
    hashes = []
    for index in range(cases):
        service, _, source = await fixture_service()
        revision = await create_fixture(service, source, types[index % len(types)])
        hashes.append(revision.content_hash)
    return {
        "cases": cases,
        "proposal_types": len(set(types[index % len(types)] for index in range(cases))),
        "stable_hashes": len(hashes),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "provider_calls": 0,
        "implementation_actions": 0,
        "destination_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=16)
    args = parser.parse_args()
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    print(json.dumps(asyncio.run(measure(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
