"""Credential-free proposal fixtures built from exact Sprint 17 contracts."""

from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.config.weakness_config import WeaknessConfiguration
from cognitive_os.domain.weakness import (
    ImpactScore,
    MiningSourceSnapshot,
    WeaknessBenchmarkCandidate,
    WeaknessEvidencePackage,
    WeaknessQueueEntry,
    WeaknessReplayCandidate,
    WeaknessReproductionAssessment,
    WeaknessReproductionStatus,
    WeaknessRevision,
    WeaknessStatus,
)
from cognitive_os.weakness.fixtures import (
    FIXTURE_TIME as WEAKNESS_FIXTURE_TIME,
)
from cognitive_os.weakness.fixtures import (
    FixtureSignalExtractor,
    fixture_profile,
    fixture_sources,
)
from cognitive_os.weakness.service import (
    ImpactFacts,
    build_candidate,
    build_evidence_package,
    build_exact_group_snapshot,
    queue_entry_for,
    score_impact,
    transition_revision,
)

FIXTURE_TIME = WEAKNESS_FIXTURE_TIME


class FixtureWeaknessProposalSource:
    def __init__(
        self,
        revision: WeaknessRevision,
        queue: WeaknessQueueEntry,
        evidence: WeaknessEvidencePackage,
        impact: ImpactScore,
    ) -> None:
        self.revision = revision
        self.queue = queue
        self.evidence = evidence
        self.impact = impact

    async def get_exact_weakness_revision(
        self, weakness_id: UUID, revision: int
    ) -> WeaknessRevision | None:
        return (
            self.revision
            if (weakness_id, revision)
            == (
                self.revision.weakness_id,
                self.revision.revision,
            )
            else None
        )

    async def get_current_weakness_revision(self, weakness_id: UUID) -> WeaknessRevision | None:
        return self.revision if weakness_id == self.revision.weakness_id else None

    async def get_exact_queue_entry(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessQueueEntry | None:
        return (
            self.queue
            if (weakness_id, weakness_revision)
            == (
                self.queue.weakness_id,
                self.queue.weakness_revision,
            )
            else None
        )

    async def get_exact_evidence_package(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessEvidencePackage | None:
        return (
            self.evidence
            if weakness_id == self.revision.weakness_id
            and weakness_revision == self.revision.revision
            else None
        )

    async def get_exact_impact_score(
        self, weakness_id: UUID, weakness_revision: int
    ) -> ImpactScore | None:
        return (
            self.impact
            if weakness_id == self.revision.weakness_id
            and weakness_revision == self.revision.revision
            else None
        )

    async def get_reproduction_assessment(
        self, weakness_id: UUID, weakness_revision: int
    ) -> WeaknessReproductionAssessment | None:
        return (
            self.evidence.reproduction
            if weakness_id == self.revision.weakness_id
            and weakness_revision == self.revision.revision
            else None
        )

    async def get_related_benchmark_candidates(
        self, weakness_id: UUID, weakness_revision: int
    ) -> tuple[WeaknessBenchmarkCandidate, ...]:
        return ()

    async def get_related_replay_candidates(
        self, weakness_id: UUID, weakness_revision: int
    ) -> tuple[WeaknessReplayCandidate, ...]:
        return ()

    async def get_required_registry_snapshots(self) -> dict[str, str]:
        return {
            "weakness": self.revision.content_hash,
            "verifiers": "1" * 64,
            "benchmarks": "2" * 64,
            "authority": "3" * 64,
        }


async def fixture_proposal_source(cases: int = 18) -> FixtureWeaknessProposalSource:
    sources = fixture_sources(max(cases, 60))
    profile = fixture_profile(sources)
    snapshot = MiningSourceSnapshot(
        mining_run_id=uuid5(NAMESPACE_URL, f"proposal-fixture:{cases}"),
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
    impact = score_impact(
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
    evidence = build_evidence_package(group, impact, signals, (), reproduction=reproduction)
    _, candidate = build_candidate(
        group,
        impact,
        evidence,
        actor="operator",
        created_at=FIXTURE_TIME,
        verifier_bundle_hash="4" * 64,
    )
    confirmed = transition_revision(
        candidate,
        WeaknessStatus.CONFIRMED,
        group=group,
        score=impact,
        evidence_coverage=Decimal("1"),
        actor="operator",
        reason="verified fixture evidence",
        verifier_bundle_hash="4" * 64,
        created_at=FIXTURE_TIME,
        configuration=WeaknessConfiguration(),
    )
    queue = queue_entry_for(
        confirmed,
        impact,
        queue_policy_hash="5" * 64,
        created_at=FIXTURE_TIME,
    )
    if queue is None:
        raise RuntimeError("fixture weakness is not queue eligible")
    return FixtureWeaknessProposalSource(confirmed, queue, evidence, impact)
