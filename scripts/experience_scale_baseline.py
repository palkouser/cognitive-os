"""CPU-only Experience Compiler scale baseline."""

from __future__ import annotations

import argparse
import json
import resource
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter

from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import build_fixture


def _p95(values: list[float]) -> float:
    return quantiles(values, n=20, method="inclusive")[18] if len(values) > 1 else values[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compilations", type=int, default=10_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.compilations < 1:
        raise SystemExit("--compilations must be positive")
    durations: list[float] = []
    source_count = event_count = assessment_count = candidate_count = 0
    manifest_bytes = 0
    started = perf_counter()
    for index in range(args.compilations):
        request, sources, profiles = build_fixture(f"seed-{index}")
        before = perf_counter()
        result = ExperienceCompiler(sources, profiles).compile(request)
        durations.append((perf_counter() - before) * 1_000)
        source_count += len(result.snapshot.source_refs)
        event_count += len(result.trajectory.entries)
        assessment_count += len(result.assessments)
        candidate_count += len(result.candidates)
        manifest_bytes += len(result.manifest.canonical_json().encode())
    report = {
        "compilations": args.compilations,
        "source_references": source_count,
        "timeline_entries": event_count,
        "step_assessments": assessment_count,
        "candidates": candidate_count,
        "manifest_bytes": manifest_bytes,
        "compilation_p50_ms": median(durations),
        "compilation_p95_ms": _p95(durations),
        "total_seconds": perf_counter() - started,
        "peak_memory_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "cpu_only": True,
        "provider_calls": 0,
        "destination_writes": 0,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
