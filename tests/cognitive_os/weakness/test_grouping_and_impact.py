from decimal import Decimal

import pytest

from cognitive_os.domain.weakness import WeaknessPriority, WeaknessType
from cognitive_os.weakness.fixtures import (
    FIXTURE_TIME,
    FixtureSignalExtractor,
    fixture_profile,
    fixture_sources,
)
from cognitive_os.weakness.service import (
    ImpactFacts,
    build_exact_group_snapshot,
    build_noop_cluster_snapshot,
    build_signature,
    score_impact,
)


async def _signals(count: int):
    from cognitive_os.domain.weakness import MiningSourceSnapshot

    sources = fixture_sources(count)
    profile = fixture_profile(sources)
    snapshot = MiningSourceSnapshot(
        mining_run_id=__import__("uuid").uuid5(__import__("uuid").NAMESPACE_URL, f"group:{count}"),
        source_refs=sources,
        registry_snapshots=("0" * 64,),
        profile_refs=(profile.content_hash,),
        created_at=FIXTURE_TIME,
    )
    return await FixtureSignalExtractor().extract(snapshot, profile), profile


@pytest.mark.asyncio
async def test_signatures_groups_and_noop_clusters_are_deterministic() -> None:
    signals, profile = await _signals(60)
    assert build_signature(signals[0]) == build_signature(signals[0])
    first = build_exact_group_snapshot(
        signals, profile_hash=profile.content_hash, created_at=FIXTURE_TIME
    )
    second = build_exact_group_snapshot(
        tuple(reversed(signals)), profile_hash=profile.content_hash, created_at=FIXTURE_TIME
    )
    assert first == second
    assert len(first.groups) == len(tuple(WeaknessType))
    clusters = build_noop_cluster_snapshot(first, created_at=FIXTURE_TIME)
    assert len(clusters.clusters) == len(first.groups)
    assert all(item.advisory for item in clusters.clusters)


@pytest.mark.asyncio
async def test_safety_floor_outranks_frequent_low_impact() -> None:
    signals, profile = await _signals(60)
    groups = build_exact_group_snapshot(
        signals, profile_hash=profile.content_hash, created_at=FIXTURE_TIME
    )
    group = groups.groups[0]
    frequent = score_impact(
        group,
        group_snapshot_hash=groups.content_hash,
        facts=ImpactFacts(evidence_coverage=Decimal("1")),
        reference_time=FIXTURE_TIME,
    )
    critical = score_impact(
        group,
        group_snapshot_hash=groups.content_hash,
        facts=ImpactFacts(
            evidence_coverage=Decimal("1"),
            safety_evidence=Decimal("1"),
        ),
        reference_time=FIXTURE_TIME,
    )
    assert critical.priority is WeaknessPriority.CRITICAL
    assert critical.final_score == Decimal("90")
    assert critical.final_score > frequent.final_score
    assert len(critical.dimensions) == 13
