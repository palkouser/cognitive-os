from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

import pytest

from cognitive_os.config.weakness_config import WeaknessConfiguration
from cognitive_os.domain.weakness import (
    QueueBlockerType,
    WeaknessPriority,
    WeaknessQueueDependency,
    WeaknessStatus,
)
from cognitive_os.weakness.errors import WeaknessLifecycleError
from cognitive_os.weakness.fixtures import (
    FIXTURE_TIME,
    FixtureSignalExtractor,
    fixture_profile,
    fixture_sources,
)
from cognitive_os.weakness.service import (
    ImpactFacts,
    build_candidate,
    build_evidence_package,
    build_exact_group_snapshot,
    build_queue_snapshot,
    queue_entry_for,
    score_impact,
    transition_revision,
)


@pytest.mark.asyncio
async def test_confirmation_and_queue_are_governed_and_deterministic() -> None:
    from cognitive_os.domain.weakness import (
        MiningSourceSnapshot,
        WeaknessReproductionAssessment,
        WeaknessReproductionStatus,
    )

    sources = fixture_sources(60)
    profile = fixture_profile(sources)
    snapshot = MiningSourceSnapshot(
        mining_run_id=uuid5(NAMESPACE_URL, "lifecycle"),
        source_refs=sources,
        registry_snapshots=("0" * 64,),
        profile_refs=(profile.content_hash,),
        created_at=FIXTURE_TIME,
    )
    signals = await FixtureSignalExtractor().extract(snapshot, profile)
    groups = build_exact_group_snapshot(
        signals, profile_hash=profile.content_hash, created_at=FIXTURE_TIME
    )
    group = next(item for item in groups.groups if item.distinct_task_count >= 2)
    score = score_impact(
        group,
        group_snapshot_hash=groups.content_hash,
        facts=ImpactFacts(evidence_coverage=Decimal("1"), correctness_evidence=Decimal("0.8")),
        reference_time=FIXTURE_TIME,
    )
    reproduction = WeaknessReproductionAssessment(
        status=WeaknessReproductionStatus.NOT_ATTEMPTED,
        attempts=(),
        required_safety_restrictions=("bounded replay only",),
        limitations=("No unrestricted execution.",),
        assessed_at=FIXTURE_TIME,
    )
    package = build_evidence_package(group, score, signals, (), reproduction=reproduction)
    _, candidate = build_candidate(
        group,
        score,
        package,
        actor="operator",
        created_at=FIXTURE_TIME,
        verifier_bundle_hash="1" * 64,
    )
    confirmed = transition_revision(
        candidate,
        WeaknessStatus.CONFIRMED,
        group=group,
        score=score,
        evidence_coverage=Decimal("1"),
        actor="operator",
        reason="recurring verified evidence",
        verifier_bundle_hash="1" * 64,
        created_at=FIXTURE_TIME,
        configuration=WeaknessConfiguration(),
    )
    assert confirmed.status is WeaknessStatus.CONFIRMED
    entry = queue_entry_for(
        confirmed,
        score,
        queue_policy_hash="2" * 64,
        created_at=FIXTURE_TIME,
    )
    assert entry is not None
    assert entry.priority is score.priority
    assert build_queue_snapshot(
        (entry,), queue_policy_hash="2" * 64, created_at=FIXTURE_TIME
    ).entries == (entry,)


def test_queue_blocker_cycles_are_rejected() -> None:
    from cognitive_os.domain.weakness import WeaknessQueueEntry, WeaknessQueueStatus

    first_id = uuid5(NAMESPACE_URL, "queue-first")
    second_id = uuid5(NAMESPACE_URL, "queue-second")

    def entry(identity, blocker):
        return WeaknessQueueEntry(
            queue_entry_id=uuid5(NAMESPACE_URL, f"entry:{identity}"),
            weakness_id=identity,
            weakness_revision=1,
            weakness_revision_hash="1" * 64,
            weakness_status=WeaknessStatus.CONFIRMED,
            priority=WeaknessPriority.HIGH,
            priority_reason="verified impact",
            blocked_by=(
                WeaknessQueueDependency(
                    blocker_type=QueueBlockerType.DEPENDS_ON_OTHER_WEAKNESS,
                    blocked_by_weakness_id=blocker,
                    evidence_reference="2" * 64,
                    reason="diagnostic dependency",
                ),
            ),
            recommended_next_analysis=__import__(
                "cognitive_os.domain.weakness", fromlist=["NextAnalysisType"]
            ).NextAnalysisType.COLLECT_MORE_EVIDENCE,
            status=WeaknessQueueStatus.BLOCKED,
            queue_policy_hash="3" * 64,
            created_at=FIXTURE_TIME,
        )

    with pytest.raises(WeaknessLifecycleError, match="cycle"):
        build_queue_snapshot(
            (entry(first_id, second_id), entry(second_id, first_id)),
            queue_policy_hash="3" * 64,
            created_at=FIXTURE_TIME,
        )
