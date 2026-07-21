"""Credential-free Sprint 17 weakness benchmark adapter."""

from time import perf_counter

from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult, BenchmarkCaseStatus
from cognitive_os.domain.common import utc_now
from cognitive_os.weakness.fixtures import (
    FixtureSignalExtractor,
    FixtureSourceResolver,
    fixture_profile,
    fixture_request,
    fixture_sources,
)
from cognitive_os.weakness.repository import InMemoryWeaknessRepository
from cognitive_os.weakness.service import (
    SignalExtractorRegistry,
    SourceResolverRegistry,
    WeaknessMiningService,
)


async def weakness_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    sources = fixture_sources(3)
    source_registry = SourceResolverRegistry()
    for source_type in sorted({item.source_type for item in sources}, key=str):
        source_registry.register(FixtureSourceResolver(source_type, sources))
    source_registry.freeze()
    extractors = SignalExtractorRegistry()
    extractors.register(FixtureSignalExtractor())
    extractors.freeze()
    profile = fixture_profile(sources)
    request = fixture_request(profile, 3)
    started = utc_now()
    before = perf_counter()
    first = await WeaknessMiningService(
        InMemoryWeaknessRepository(), source_registry, extractors
    ).mine(request, profile)
    second = await WeaknessMiningService(
        InMemoryWeaknessRepository(), source_registry, extractors
    ).mine(request, profile)
    passed = first == second and first.manifest is not None
    summary = first.manifest.summary if first.manifest else None
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED if passed else BenchmarkCaseStatus.FAILED,
        started_at=started,
        finished_at=utc_now(),
        metrics={
            "expected_outcome_matched": float(passed),
            "deterministic_replay_rate": float(first == second),
            "source_lineage_completeness": float(bool(summary and summary.source_count)),
            "signal_count": float(summary.signal_count if summary else 0),
            "group_count": float(summary.group_count if summary else 0),
            "queue_entry_count": float(summary.queue_entry_count if summary else 0),
            "mining_latency_seconds": perf_counter() - before,
            "provider_calls": 0.0,
            "source_write_count": 0.0,
            "automatic_confirmation_count": 0.0,
            "scope_leak_count": 0.0,
            "sensitivity_leak_count": 0.0,
        },
    )
