"""Measure the deterministic CPU-only Corpus Factory scale path."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from time import perf_counter

from cognitive_os.corpus.factory import CorpusFactory
from cognitive_os.corpus.fixtures import FixtureArtifactStore, build_corpus_fixture
from cognitive_os.corpus.repository import InMemoryCorpusRepository


async def measure(cases: int) -> dict[str, object]:
    durations = []
    routed = quarantined = bytes_processed = 0
    started = perf_counter()
    for index in range(cases):
        request, source = build_corpus_fixture(f"seed-{index}")
        case_started = perf_counter()
        result = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
            request, source
        )
        durations.append((perf_counter() - case_started) * 1_000)
        routed += int(result.items[0].current_status.value == "routed")
        quarantined += int(result.items[0].current_status.value == "quarantined")
        bytes_processed += sum(len(item.data) for item in source.materials)
    ordered = sorted(durations)
    return {
        "cases": cases,
        "routed": routed,
        "quarantined": quarantined,
        "source_bytes": bytes_processed,
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[max(0, int(cases * 0.95) - 1)], 3),
        "elapsed_seconds": round(perf_counter() - started, 3),
        "provider_calls": 0,
        "destination_writes": 0,
        "training_actions": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=10_000)
    args = parser.parse_args()
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    print(json.dumps(asyncio.run(measure(args.cases)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
