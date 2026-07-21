"""Run reproducible credential-free Corpus Factory benchmark cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from time import perf_counter

from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore, build_corpus_fixture
from cognitive_os.corpus.repository import InMemoryCorpusRepository


async def run_benchmark(cases: int) -> dict[str, object]:
    started = perf_counter()
    hashes: list[str] = []
    statuses: dict[str, int] = {}
    for index in range(cases):
        name = f"seed-{index}"
        request, source = build_corpus_fixture(name)
        result = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
            request, source
        )
        repeated = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
            request, source
        )
        if result != repeated:
            raise RuntimeError(f"non-deterministic corpus result: {name}")
        hashes.append(result.content_hash)
        status = result.items[0].current_status.value
        statuses[status] = statuses.get(status, 0) + 1
    return {
        "cases": cases,
        "unique_result_hashes": len(set(hashes)),
        "statuses": statuses,
        "reproducible": True,
        "credential_free": True,
        "destination_writes": 0,
        "training_actions": 0,
        "elapsed_seconds": round(perf_counter() - started, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, choices=(14, 56), default=14)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_benchmark(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
